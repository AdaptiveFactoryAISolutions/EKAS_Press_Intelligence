'use strict';
// Fixed explanations + saved server evidence. No causal inference in this renderer.
(() => {
  let sequence=0;
  const make=(tag,value,cls)=>{const n=document.createElement(tag);if(value!==undefined)n.textContent=String(value);if(cls)n.className=cls;return n;};
  const number=value=>typeof value==='number'&&Number.isFinite(value)?new Intl.NumberFormat('en-US',{maximumFractionDigits:3}).format(value):'Not recorded';
  const time=value=>{const date=new Date(value);return value&&Number.isFinite(date.getTime())?new Intl.DateTimeFormat('en-US',{year:'numeric',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23',timeZone:'UTC'}).format(date)+' UTC':'Not recorded';};
  const sentence=(parent,value)=>parent.append(make('p',value));
  const section=(parent,title)=>{const s=make('section',undefined,'report-section');s.append(make('h2',title));parent.append(s);return s;};
  const button=(title,fn)=>{const b=make('button',title,'secondary');b.type='button';b.addEventListener('click',fn);return b;};
  const terms=[['Simulation','A computer test of a process. It does not operate a real machine.'],['Stroke','One press cycle. A stroke does not always give a finished part.'],['Die station','One position in the die where the strip undergoes a process step.'],['Signal','One measured or calculated value, such as speed or a part count.'],['Primary reading','A reading in the original stored sensor file. The report does not add readings between stored points.'],['Quality code','A stored code for the condition of a reading. It is not a part-quality test.'],['Target','A configured value that the control system tries to keep. It is not an acceptance limit.'],['UTC','The reference time used for the timestamps in this report.']];
  function graph(parent,title,signals,start,end,target) {
    const box=make('figure',undefined,'report-figure');box.append(make('h3',title));
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
    const width=800,height=230,pad=55;
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('role','img');
    const valid=signals.filter(s=>s.good_count>0);
    if(!valid.length){sentence(box,'The stored readings are not available for this graph.');parent.append(box);return;}
    const peak=Math.max(1,...valid.map(s=>s.maximum),typeof target==='number'?target:0);
    const bottom=Math.min(0,...valid.map(s=>s.minimum));
    const rough=(peak-bottom)/4,magnitude=10**Math.floor(Math.log10(rough));
    const step=([1,2,2.5,5,10].find(v=>v>=rough/magnitude)??10)*magnitude;
    const top=bottom+Math.ceil((peak-bottom)/step)*step;
    const lo=Date.parse(start),hi=Date.parse(end),span=Math.max(60000,Math.ceil((hi-lo)/60000)*60000);
    const x=t=>pad+(Date.parse(t)-lo)/span*(width-pad*2);
    const y=v=>height-pad-(v-bottom)/(top-bottom)*(height-pad*1.5);
    const shape=(tag,attrs)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));svg.append(n);return n;};
    const label=(value,x,y)=>{shape('text',{x,y,'font-size':13,fill:'currentColor'}).textContent=value;};
    shape('line',{x1:pad,y1:y(bottom),x2:width-pad,y2:y(bottom),stroke:'#6b7280'});
    shape('line',{x1:pad,y1:y(bottom),x2:pad,y2:y(top),stroke:'#6b7280'});
    for(let value=bottom;value<=top+step/1000;value+=step)label(number(value),3,y(value)+4);
    for(let i=0;i<=4;i++){const minutes=span/60000*i/4;label(number(minutes),pad+(width-pad*2)*i/4-8,height-27);}
    label('Minutes from the start',width/2-70,height-4);
    if(typeof target==='number')shape('line',{x1:pad,y1:y(target),x2:width-pad,y2:y(target),stroke:'#6b7280','stroke-dasharray':'6 5'});
    const colors=['#087e8b','#ad4f19'];let reduced=false;
    for(const [i,s] of valid.entries()){
      for(const p of s.points)shape('circle',{cx:x(p.time),cy:y(p.value),r:2.8,fill:colors[i%colors.length]});
      sentence(box,`${i===0?'Blue':'Orange'} dots: ${s.label.toLowerCase()}. Lowest reading: ${number(s.minimum)} ${s.unit}. Highest reading: ${number(s.maximum)} ${s.unit}.`);
      reduced||=s.plot_reduced;
    }
    svg.setAttribute('aria-label',`${title}. ${valid[0].unit}. The horizontal scale shows minutes from the start. Stored good readings only.`);
    box.insertBefore(svg,box.children[1]);
    const caption=make('figcaption',`Left scale: ${valid[0].unit}. Dots show stored readings with good quality codes. The report does not connect the dots.`);
    box.append(caption);
    if(typeof target==='number')sentence(box,`The dashed line shows the configured target of ${number(target)} ${valid[0].unit}. It is not an acceptance limit.`);
    if(reduced)sentence(box,'The graph shows selected stored points. The totals and ranges use all stored readings.');
    parent.append(box);
  }
  function render(root,r){
    const actions=make('div',undefined,'report-actions');
    actions.append(button('Back to runs',()=>window.EKASSetup.view('jobs')),button('View measurements',()=>window.EKASSetup.openDataset(r.dataset_id)),button('Print or save as PDF',()=>window.print()));root.append(actions);
    root.append(make('h1',r.title),make('p','Simulation practice only','report-status'));
    const summary=section(root,'1. What happened?');
    sentence(summary,'The software completed this press simulation. Some data checks may still need attention.');
    const produced=r.signals['COUNT-PRODUCED'],packed=r.signals['COUNT-PACKED'];
    const cards=make('div',undefined,'report-facts');
    for(const [s,label] of [[produced,'parts produced'],[packed,'parts packed']]){
      const card=make('div');card.append(make('strong',s.last?`${number(s.last.value)} ${label}`:'Last reading is not available'));
      sentence(card,s.last?`Last stored reading: ${time(s.last.time)}`:`${s.label}: the final stored observation is missing or unusable.`);cards.append(card);
    }summary.append(cards);
    if(r.balance.status==='agrees'){sentence(summary,`${number(r.balance.in_line)} parts remained in the line at the last observation. The stored counts agree.`);sentence(summary,`The model recorded ${number(r.balance.rejected)} rejected parts.`);}
    else if(r.balance.status==='differs')sentence(summary,'The stored part counts do not agree. Inspect the readings before you use these totals.');
    else sentence(summary,'The final part balance is not available. It needs good readings for all six counts at the same final time.');
    sentence(summary,'Use this run to learn the system. These results do not give approval for real equipment.');

    const setup=section(root,'2. Which equipment and settings did you test?');
    sentence(setup,'This is a computer model of the press line. It is not data from your customer’s equipment.');
    sentence(setup,'The saved run does not identify a customer, site, or operator.');
    sentence(setup,'The strip moves from the reel through the loop pit, straightener, feeder, and die stations.');
    sentence(setup,'Scrap goes to chutes or conveyors. Finished parts go through the hot-water washer, then to manual packing.');
    const list=make('ul');
    for(const line of [`Press target: ${number(r.setup.speed_spm)} strokes per minute.`,`Washer target: ${number(r.setup.washer_temperature_c)} degrees Celsius.`,`Die stations: ${number(r.setup.stations)}.`,`Packing: ${number(r.setup.packers)} people; ${number(r.setup.packing_rate_per_min)} parts per minute for each person.`,`Test case: ${r.setup.case}.`])list.append(make('li',line));
    setup.append(list);
    if(r.setup.fault_count>0){sentence(setup,`The setup requests ${number(r.setup.fault_count)} fault event(s). This is a test instruction, not a diagnosis.`);for(const name of r.setup.requested_cases)sentence(setup,`Requested test: ${name}.`);sentence(setup,'A selected fault does not confirm the cause of an observed result.');}
    const times=section(root,'3. When did this happen?');
    sentence(times,`First observation: ${time(r.start)}. Last observation: ${time(r.end)}.`);
    sentence(times,`The computer created the job at ${time(r.created_at)}.`);
    sentence(times,`The job completed at ${time(r.completed_at)}.`);
    sentence(times,'The observation dates belong to the simulation. They are not the dates of a real production shift.');

    const charts=section(root,'4. How do you read the graphs?');
    sentence(charts,'Read each graph from left to right. The bottom scale shows time. The left scale gives the measurement and its unit.');
    sentence(charts,'Each graph uses its own scale. Do not compare the heights of signals with different units.');
    graph(charts,'Press speed',[r.signals['SIC-1500.PV']],r.start,r.end,r.setup.speed_spm);
    sentence(charts,`The file contains ${number(r.signals['SIC-1500.PV'].stored_count)} stored speed readings. The recorder can discard small changes to decrease file size.`);
    sentence(charts,'A small number of stored readings cannot show every movement of the press.');
    graph(charts,'Washer temperature',[r.signals['TI-WASH']],r.start,r.end,r.setup.washer_temperature_c);
    sentence(charts,'Temperature readings do not confirm that the parts were clean. This report does not include a part-cleanliness test.');
    graph(charts,'Parts produced and packed',[produced,packed],r.start,r.end);

    const balance=section(root,'5. Why are produced and packed counts different?');
    sentence(balance,'A produced part must pass through the washer before an operator can pack it. Some parts can remain in the line.');
    const table=make('table'),caption=make('caption','Last stored counts. The time matters when you compare readings.');table.append(caption);
    const tr=make('tr');for(const h of ['Measurement','Count','Observation time (UTC)']){const th=make('th',h);th.scope='col';tr.append(th);}const head=make('thead');head.append(tr);table.append(head);const body=make('tbody');
    for(const name of ['COUNT-STROKES','COUNT-PRODUCED','COUNT-PACKED','COUNT-WASHER','COUNT-DISCHARGE','COUNT-PACK-QUEUE','COUNT-REJECTED']){
      const s=r.signals[name],row=make('tr');for(const value of [s.label,s.last?number(s.last.value):'Not available',time(s.latest_observation_time)])row.append(make('td',value));body.append(row);
    }table.append(body);balance.append(table);
    if(r.balance.status==='agrees'){sentence(balance,`Produced minus packed equals ${number(r.balance.produced_minus_packed)} parts.`);sentence(balance,`${number(r.balance.in_line)} parts remain on the conveyor, in the washer, or in the packing queue. The model also recorded ${number(r.balance.rejected)} rejected parts.`);}
    sentence(balance,'The die stations must fill before the first finished part exits. A stroke count is not a packed-part count.');
    sentence(balance,'The report does not assign other count differences to a cause without more evidence.');
    sentence(balance,'The earlier measurement graph can stop before the final stored reading. Always compare counts at the same time.');

    const checks=section(root,'6. Which checks passed?');
    const engineering=r.validation.engineering_status;
    sentence(checks,engineering==='passed'?'The model’s quantity checks passed. These checks compare quantities within the model.':engineering==='failed'?'The model’s quantity checks failed. Do not use these results as an accepted example.':'The model’s quantity-check result is not available. Do not treat an unknown result as a pass.');
    sentence(checks,'A passed check does not confirm accuracy against real equipment.');
    sentence(checks,r.validation.native_status==='passed'?'The recorded native data checks passed. The run remains practice only.':r.validation.native_status==='findings'?'The native data checks reported findings. The run is not fully validated.':'The native data-check result is not available. The report cannot confirm that these checks passed.');
    for(const f of r.validation.findings){checks.append(make('h3',f.title));sentence(checks,f.explanation);}
    for(const s of Object.values(r.signals))if(!s.stored_count||s.unusable_count)sentence(checks,`${s.label}: ${number(s.unusable_count)} unusable stored reading(s); ${number(s.good_count)} good stored reading(s). Missing or unusable values are not zero.`);

    const next=section(root,'7. What should you do next?'),steps=make('ol');
    const guidance=r.setup.fault_count===0?['Keep this run as your example without an injected fault.','Use the same settings for a separate run with one selected fault.']:r.setup.fault_count>0?['Keep this run as your fault-practice example.','Make a separate run without an injected fault. Keep the other settings the same.']:['Check the saved test-case settings before you compare runs.'];
    guidance.push('Compare the same measurements over the same period.','Record the differences that you can see.','Correct the validation problems before you use the data to test diagnostic accuracy.');
    for(const line of guidance)steps.append(make('li',line));next.append(steps);
    sentence(next,'This report does not confirm safe operation, part quality, cleaning quality, or the cause of a real machine fault.');

    const glossary=section(root,'8. What do the technical terms mean?'),dl=make('dl');
    for(const [term,meaning] of terms)dl.append(make('dt',term),make('dd',meaning));glossary.append(dl);
    const evidence=section(root,'9. How was this report made?');
    sentence(evidence,'The report uses the saved run settings, recorded check results, and original public sensor file. It does not run the simulation again.');
    sentence(evidence,r.provenance.summaries);sentence(evidence,r.provenance.plot);
    sentence(evidence,'All summary counts and ranges cover the full primary file. The graph can show fewer points to keep the page usable.');
    sentence(evidence,'The report rounds displayed values. The stored values stay unchanged.');
    sentence(evidence,`Report version: ${r.report_version}. Run: ${r.job_id}.`);
    const detail=make('details');detail.append(make('summary','Show source identifiers and recorded check names'),make('pre',JSON.stringify({provenance:r.provenance,validation:r.validation},null,2)));evidence.append(detail);
    const language=section(root,'10. Language review');sentence(language,`Reference: ${r.language.reference}.`);sentence(language,r.language.note);
  }
  async function open(id){
    const request=++sequence,root=document.getElementById('view-report');
    if(!root)return;
    window.EKASSetup.view('report');root.replaceChildren(make('p','Reading the saved run…'));root.setAttribute('aria-busy','true');
    try{const r=await window.EKASSetup.api(`/jobs/${encodeURIComponent(id)}/practice-report`);if(request!==sequence)return;root.replaceChildren();render(root,r);root.querySelector('h1').tabIndex=-1;root.querySelector('h1').focus();}
    catch(error){if(request!==sequence)return;root.replaceChildren(make('h1','The report is not available'),make('p',error.message),button('Try again',()=>open(id)),button('Back to runs',()=>window.EKASSetup.view('jobs')));}
    finally{if(request===sequence)root.removeAttribute('aria-busy');}
  }
  window.PracticeReport={open};
})();
