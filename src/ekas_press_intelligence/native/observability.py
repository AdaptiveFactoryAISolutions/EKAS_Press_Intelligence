"""Availability profiles derived from public native artifacts, never a new simulation."""
from __future__ import annotations
import csv
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import shutil
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from .data import dataset_info,public_files,resolve_public_file

BATCH_ROWS=16384
AVAILABILITY_FILES={'SOURCE_AVAILABILITY.json','SOURCE_AVAILABILITY.md'}


def profile_contract(plant,repo_root):
    """Read actual plant withholding metadata only after native source verification."""
    if not isinstance(plant,str) or not re.fullmatch(r'[a-z][a-z0-9_]*',plant):raise ValueError('INVALID_PARAMETERS: plant must name a native registered plant')
    from .bootstrap import activate
    verified=activate()
    if Path(verified['repository']).resolve()!=Path(repo_root).resolve():raise ValueError('INVALID_NATIVE_RUNTIME: repository mismatch')
    from historiansim.plants import get_plant
    native=get_plant(plant)
    names=[tag.name for tag in native.tags()];withheld=list(native.hard_mode_withheld)
    if len(names)!=len(set(names)) or set(withheld)-set(names):raise ValueError('INVALID_NATIVE_PROFILE: native withholding references unknown or duplicate tags')
    journal={}
    module=native.unit_cls.__module__.rsplit('.',1)[0]+'.cycles'
    try:cycles=importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name!=module:raise
    else:
        log=getattr(cycles,'EventLog',None)
        if log is not None:
            # An empty projection exposes declared acquisition channel metadata only.
            # It neither evolves a plant nor reads a physical event/truth ledger.
            projection=log().public_status_columns()
            if len(projection)!=4 or not isinstance(projection[3],dict):raise ValueError('INVALID_NATIVE_PROFILE: public event mapping is unavailable')
            journal={int(code):str(tag) for code,tag in projection[3].items()}
            if set(journal.values())-set(names):raise ValueError('INVALID_NATIVE_PROFILE: journal channel references unknown tags')
    origin=Path(inspect.getfile(native.unit_cls)).resolve()
    contract={'plant':plant,'plant_tags':names,'withheld_tags':withheld,'journal_status_tags':journal,'runtime_kind':verified['kind'],'model_sha256':hashlib.sha256(origin.read_bytes()).hexdigest()}
    contract['contract_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    return contract


def _source_folder(value):
    source=Path(value)
    if not source.is_dir() or any(p.is_symlink() for p in (source,*source.parents)) or any(p.is_symlink() for p in source.iterdir()):raise ValueError('OBSERVABILITY_SOURCE_FORBIDDEN: public source must not contain symlinks')
    if (source/'metadata').exists() or (source/'FAULT_ANSWER_KEY.md').exists():raise ValueError('OBSERVABILITY_SOURCE_FORBIDDEN: choose public challenge artifacts, never private generation output')
    return source


def _tag_master(source):
    path=resolve_public_file(source,'tags.csv')
    if path.stat().st_size>8388608:raise ValueError('OBSERVABILITY_METADATA_LIMIT: native tag dictionary exceeds8MB')
    with path.open(newline='',encoding='utf-8') as stream:
        reader=csv.reader(stream);header=next(reader,[]);rows=list(reader)
    if header.count('tag')!=1 or len(header)!=len(set(header)):raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: unambiguous native tag dictionary required')
    index=header.index('tag')
    if any(len(row)!=len(header) for row in rows):raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: malformed tag dictionary')
    names=[row[index] for row in rows]
    if not names or any(not n for n in names) or len(names)!=len(set(names)):raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: tag names must be present and unique')
    return header,rows,names


def _stream(source,destination,columns=None,tags=None,codes=None,report=None):
    file=pq.ParquetFile(source)
    schema=file.schema_arrow if columns is None else pa.schema([file.schema_arrow.field(name) for name in columns],metadata=file.schema_arrow.metadata)
    retained=pa.array(tags,type=pa.string()) if tags is not None else None
    allowed_codes=pa.array(codes,type=pa.int64()) if codes is not None else None
    read=written=0
    with pq.ParquetWriter(destination,schema,compression='snappy') as writer:
        for batch in file.iter_batches(batch_size=BATCH_ROWS,columns=columns,use_threads=False):
            read+=batch.num_rows
            if report is not None:report['max_batch_rows']=max(report['max_batch_rows'],batch.num_rows)
            if retained is not None:batch=batch.filter(pc.is_in(pc.cast(batch.column('tag'),pa.string()),value_set=retained))
            if allowed_codes is not None:batch=batch.filter(pc.is_in(pc.cast(batch.column('event_code'),pa.int64()),value_set=allowed_codes))
            if batch.num_rows:writer.write_batch(batch);written+=batch.num_rows
    return {'source_rows':read,'retained_rows':written,'removed_rows':read-written}


def _disclosure(profile):
    return ('# Source availability disclosure\n\n'
        f'Profile: **{profile}**. This export uses observations from the same existing physical run. '
        'It does not simulate another run, repair sensors, restore missing observations, interpolate values or alter acquisition quality.\n\n'
        'Available tags identify retained source channels, not a guarantee of good quality or discriminative evidence. '
        'The process description and PFD describe the physical design inventory; consult tags.csv and SOURCE_AVAILABILITY.json for channels actually retained. '
        'Sparse information may leave competing explanations unresolved. No claim that every root cause is uniquely solvable from this restricted export is made.\n\n'
        'Raw observations retain their recorded timestamps, values and quality. Regular grids retain the native source reconstruction and nulls. '
        'Public digital events retain their measured clock and quality; channel restrictions, if any, are explicit in the availability manifest.\n\n')


def _missing_channels_message(missing):
    return (' Missing required channels: '+', '.join(sorted(missing))+'. '
        'The source may use an earlier model version or be incomplete. Select a current dataset, '
        'or use its original verified runtime. Missing observations cannot be created or restored by export.')


def execute_observability(parameters,target,repo_root,progress=None):
    if not isinstance(parameters,dict) or set(parameters)-{'dataset_dir','profile','plant'} or not {'dataset_dir','profile','plant'}.issubset(parameters):raise ValueError('INVALID_PARAMETERS: registered public dataset, native plant and availability profile required')
    profile=parameters['profile']
    if not isinstance(profile,str) or profile not in {'enhanced','sparse'}:raise ValueError('INVALID_PARAMETERS: profile must be enhanced or sparse')
    source=_source_folder(parameters['dataset_dir']);target=Path(target)
    if any(p.is_symlink() for p in (target,*target.parents)):raise ValueError('INVALID_TARGET: symbolic link path')
    src=source.resolve();dst=target.resolve()
    if dst==src or dst.is_relative_to(src) or src.is_relative_to(dst):raise ValueError('INVALID_TARGET: profile target must be separate from its source')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):raise ValueError('INVALID_TARGET: fresh empty target required')
    def phase(value):
        if progress:progress(value)
    phase('verifying_native_availability_contract')
    contract=profile_contract(parameters['plant'],repo_root)
    header,tag_rows,names=_tag_master(source);known=set(names);core=set(contract['plant_tags']);withheld=set(contract['withheld_tags'])
    manifest_path=source/'SOURCE_AVAILABILITY.json'
    previous=None
    if manifest_path.exists():
        path=resolve_public_file(source,'SOURCE_AVAILABILITY.json')
        if path.stat().st_size>2097152:raise ValueError('OBSERVABILITY_METADATA_LIMIT: source availability manifest exceeds2MB')
        try:previous=json.loads(path.read_text())
        except ValueError:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: source availability manifest is invalid') from None
        if not isinstance(previous,dict) or previous.get('profile') not in {'sparse','enhanced'}:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: source availability profile is unknown')
    if profile=='enhanced' and (core-known or (previous and previous['profile']=='sparse')):raise ValueError('OBSERVABILITY_CANNOT_RESTORE: enhanced requires the complete original source channels; sparse observations cannot be restored'+(_missing_channels_message(core-known) if core-known else ' Use the original full source dataset.'))
    if (core-withheld)-known:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: source lacks native core channels required even by its sparse profile'+_missing_channels_message((core-withheld)-known))
    retained=[name for name in names if profile=='enhanced' or name not in withheld]
    if not retained:raise ValueError('OBSERVABILITY_EMPTY: no retained source channels')
    restriction_applied=len(retained)<len(names)
    availability_note=('This plant declares no withheld channels; the sparse profile retains all available source observations.' if profile=='sparse' and not withheld else '')
    disclosure=_disclosure(profile)+(availability_note+'\n\n' if availability_note else '')
    info=dataset_info(source);grid_channels=set(info['grid']['columns'])-{'timestamp'}
    if profile=='enhanced' and core-grid_channels:raise ValueError('OBSERVABILITY_CANNOT_RESTORE: source grid lacks native core channels even if the dictionary names them'+_missing_channels_message(core-grid_channels))
    if (core-withheld)-grid_channels:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: source grid lacks channels required by its sparse profile'+_missing_channels_message((core-withheld)-grid_channels))
    digests=public_files(source)
    target.mkdir(parents=True,exist_ok=True);target.chmod(0o700);public=target/'public';public.mkdir()
    visible=set(retained);streaming={'batch_rows':BATCH_ROWS,'max_batch_rows':0};artifacts={}
    phase('streaming_existing_public_observations')
    for entry in digests:
        name=entry['name']
        if name in AVAILABILITY_FILES:continue
        origin=resolve_public_file(source,name);dest=public/name
        if name.endswith('.parquet'):
            schema=pq.ParquetFile(origin).schema_arrow;fields=schema.names
            if name==info['raw_file']:
                if set(fields)!={'timestamp','tag','value','quality'}:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: native primary schema required')
                if profile=='enhanced':shutil.copyfile(origin,dest)
                else:artifacts[name]=_stream(origin,dest,tags=retained,report=streaming)
            elif name=='cycle_event_journal.parquet':
                if 'tag' in fields:
                    if set(fields)-{'timestamp','tag','value','quality','event_code','count'}:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: public tagged event schema contains unsupported fields')
                    if profile=='enhanced':shutil.copyfile(origin,dest)
                    else:artifacts[name]=_stream(origin,dest,tags=retained,report=streaming)
                else:
                    if set(fields)!={'timestamp','event_code','count','quality'}:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: public digital journal schema is unsupported')
                    mapping=contract['journal_status_tags']
                    if not mapping:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: native journal channel mapping is unavailable')
                    if set(mapping.values()).issubset(visible):
                        shutil.copyfile(origin,dest);artifacts[name]={'mode':'byte-exact public journal copy','channel_mapping':mapping}
                    else:
                        codes=[code for code,tag in mapping.items() if tag in visible]
                        artifacts[name]=_stream(origin,dest,codes=codes,report=streaming)
                        artifacts[name]['disclosure']='Unattributable code-1 bad-quality events are omitted when only part of the journal channel mapping remains visible.'
            else:
                if 'timestamp' not in fields or set(fields)-{'timestamp'}-known:raise ValueError('OBSERVABILITY_SCHEMA_MISMATCH: wide public observations reference unknown channels')
                columns=[name for name in fields if name=='timestamp' or name in visible]
                if profile=='enhanced' or columns==fields:shutil.copyfile(origin,dest)
                else:artifacts[name]=_stream(origin,dest,columns=columns,report=streaming)
        elif name=='tags.csv':
            if profile=='enhanced':shutil.copyfile(origin,dest)
            else:
                index=header.index('tag')
                with dest.open('w',newline='',encoding='utf-8') as stream:
                    writer=csv.writer(stream,lineterminator='\n');writer.writerow(header);writer.writerows(row for row in tag_rows if row[index] in visible)
        elif name in {'CHALLENGE.md','PROCESS_DESCRIPTION.md'}:
            if origin.stat().st_size>2097152:raise ValueError('OBSERVABILITY_METADATA_LIMIT: public process/task document exceeds2MB')
            text=origin.read_text(encoding='utf-8')
            if profile=='sparse':text=re.sub(r'Every\s+event\s+has\s+a\s+single,\s+known\s+root\s+cause,\s+and\s+every\s+root\s+cause\s+can\s+be\s+determined\s+from\s+the\s+files\s+in\s+this\s+folder\s+alone\.','The physical source run is unchanged; this availability restriction may leave causal alternatives unresolved.',text,flags=re.I)
            dest.write_text(disclosure+'---\n\n'+text,encoding='utf-8')
        else:shutil.copyfile(origin,dest)
    phase('writing_availability_provenance')
    (public/'SOURCE_AVAILABILITY.md').write_text(disclosure,encoding='utf-8')
    availability={'schema_version':1,'profile':profile,'plant':parameters['plant'],'same_physical_run':True,'resimulated':False,'interpolation_performed':False,'retained_tag_count':len(retained),'available_tags':retained,'withheld_tags':contract['withheld_tags'] if profile=='sparse' else [],'removed_source_tags':[name for name in names if name not in visible],'missing_source_core_tags':[name for name in contract['plant_tags'] if name not in known],'source_digests':digests,'output_artifacts':public_files(public),'native_contract_sha256':contract['contract_sha256'],'runtime_kind':contract['runtime_kind'],'event_artifact_handling':artifacts,'streaming':streaming,'disclosure':'Information restriction of existing public observations. Retained sample values, quality and timestamp order are preserved. Sparse uniqueness of causal diagnosis is not promised.'}
    availability.update(restriction_applied=restriction_applied,availability_note=availability_note)
    (public/'SOURCE_AVAILABILITY.json').write_text(json.dumps(availability,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    result={'operation':'observability_export','profile':profile,'plant':parameters['plant'],'public_directory':'public','dataset':dataset_info(public),'source_digests':digests,'retained_tag_count':len(retained),'source_tag_count':len(names),'withheld_tag_count':len(availability['withheld_tags']),'same_physical_run':True,'resimulated':False,'native_contract_sha256':contract['contract_sha256'],'streaming':streaming,'files':public_files(public),'validation_performed':False,'passed':None}
    result.update(restriction_applied=restriction_applied,availability_note=availability_note)
    phase('observability_profile_exported')
    return result
