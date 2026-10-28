"""Structured objective/scope interpretation; never maps language to causes."""
import re


class ClarificationRequired(ValueError):
    pass


def interpret(question,asset,start,end):
    words=question.lower()
    referenced=re.findall(r'\b(press|feeder|decoiler|line)\s*(\d+)\b',words)
    for kind,number in referenced:
        supported=(kind=='line' and int(number)==3) or (kind!='line' and int(number)==27)
        if not supported:
            raise ClarificationRequired('The referenced asset is unavailable in this reference cell.')
    referenced_assets={f'{kind} {int(number)}' for kind,number in referenced}
    if referenced_assets and asset.lower()!='line 03' and asset.lower() not in referenced_assets:
        raise ClarificationRequired('The asset named in the objective conflicts with the selected scope. Select the intended asset or the line.')
    if re.search(r'\b(yesterday|tomorrow|today)\b|\b(last|previous)\s+(shift|day|week|month|year)\b|\b\d{4}-\d{2}-\d{2}\b',words):
        raise ClarificationRequired('Historical/calendar period interpretation is unavailable. Select the exact elapsed campaign period.')
    if re.search(r'\b(energy|electricity|profit|savings|cost|revenue)\b',words):
        raise ClarificationRequired('This investigation endpoint evaluates observed production evidence. Financial estimates require explicit assumptions; no financial metric was substituted.')
    return {'action':'INVESTIGATE','asset':asset,'period':{'start_s':start,'end_s':end},'objective':question}
