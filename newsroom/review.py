"""S04 검수·승인: 원문 근거/본문 해시 확인, 자동 PASS 실패 시 승인 차단."""
import os, json, re, hashlib, hmac
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import text
from openai import OpenAI
from pydantic import BaseModel, Field
from newsroom.persistence import checked_facts

CHECKS=["수치·산식·분모를 원자료와 대조","연도·지역·단위 확인","원인·효과·폴리곤 비율 과장 없음","출처 및 원문 대조 범위 확인"]
def decode(v): return json.loads(v) if isinstance(v,str) else v

def context(conn,id,locked=False):
    sql="""SELECT a.*,i.analysis_id AS idea_analysis_id FROM articles a
           JOIN story_ideas i ON a.story_idea_id=i.id WHERE a.id=:id"""
    row=conn.execute(text(sql+(" FOR UPDATE" if locked else "")),{"id":id}).mappings().first()
    if not row: raise ValueError("기사를 찾을 수 없습니다.")
    a=dict(row)
    a["validation_result"]=decode(a["validation_result"]) if a["validation_result"] else None
    a["evidence"]=[]
    edges=conn.execute(text("SELECT evidence_role,analysis_id,source_document_id FROM article_evidence WHERE article_id=:id ORDER BY id"),{"id":id}).mappings().all()
    for edge in edges:
        e=dict(edge); rid=e["analysis_id"] if e["evidence_role"]=="STATISTIC" else e["source_document_id"]
        if e["evidence_role"]=="STATISTIC":
            x=conn.execute(text("SELECT facts_json,source_info_json,verification_status,data_as_of FROM analysis_snapshots WHERE id=:id"),{"id":rid}).mappings().first() if rid else None
        else:
            x=conn.execute(text("SELECT title,source_url,source_org,content_excerpt,verification_status FROM source_documents WHERE id=:id"),{"id":rid}).mappings().first() if rid else None
        e["payload"]=dict(x) if x else None
        if x and e["evidence_role"]=="STATISTIC":
            e["payload"]["facts_json"]=decode(e["payload"]["facts_json"])
            e["payload"]["source_info_json"]=decode(e["payload"]["source_info_json"])
        a["evidence"].append(e)
    return a

def digest(a):
    material=[(e["evidence_role"],e["analysis_id"],e["source_document_id"],e["payload"]) for e in a["evidence"]]
    return hashlib.sha256(json.dumps([a["title"],a["content"],material],sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def grounding(a):
    errors=[]; stats=[e for e in a["evidence"] if e["evidence_role"]=="STATISTIC"]
    if len(stats)!=1 or stats[0]["analysis_id"]!=a["idea_analysis_id"]:
        errors.append({"category":"SOURCE","reason":"기사거리와 연결된 통계 근거가 정확히 하나 필요합니다."})
    for e in a["evidence"]:
        p=e["payload"]
        if not p: errors.append({"category":"SOURCE","reason":"연결 근거 누락"})
        elif e["evidence_role"]=="STATISTIC" and (p["verification_status"]!="PASSED" or not checked_facts(p["facts_json"])):
            errors.append({"category":"FACT_SHEET","reason":"검증되지 않은 통계"})
        elif e["evidence_role"]=="CONTEXT" and (p["verification_status"]!="VERIFIED" or not p["content_excerpt"]):
            errors.append({"category":"SOURCE","reason":"원문 미확인 맥락 근거"})
    return errors

def numeric(a):
    stats=[e for e in a["evidence"] if e["evidence_role"]=="STATISTIC" and e["payload"]]
    if len(stats)!=1:return []
    f=stats[0]["payload"]["facts_json"]; content=a["title"]+"\n"+a["content"]; out=[]
    for pattern,key,allow in [
        (r"고령\s*보행자\s*사고(?:\s*건수)?\s*(?:는|가|은|:|총)?\s*(\d[\d,]*)\s*건","accidents",Decimal(0)),
        (r"(?:고령인구|65세\s*이상\s*(?:거주)?인구)\s*1만\s*명당\s*(?:고령\s*보행자\s*)?사고(?:율|\s*건수)?\s*(?:는|가|은|:)?\s*(\d+(?:\.\d+)?)\s*건","accidents_per_10000_residents",Decimal("0.051"))]:
        if f.get(key) is None:continue
        for m in re.finditer(pattern,content):
            if abs(Decimal(m.group(1).replace(",",""))-Decimal(str(f[key])))>allow:
                out.append({"category":"NUMBER","excerpt":m.group(0),"reason":f"{key}: 근거값 {f[key]}"})
    return out

class Finding(BaseModel):
    category:str
    excerpt:str
    reason:str
    suggestion:str
class Review(BaseModel):
    findings:list[Finding]=Field(default_factory=list)

PROMPT="""한국 데이터 저널리즘 사실 검수자. 실제 수정할 오류만 보고하라.
[현재 날짜]
사용자 입력의 현재 시점이 아니라 요청에 전달된 today_kst가 실제 기준이다.
학습 당시 날짜(예: 2024년)를 현재로 가정하지 말라.
과거 사고연도 자료는 실제 Fact Sheet에 존재하면 '미래 데이터' 오류가 아니다.
[숫자·분모]
Fact Sheet의 연도·지역·사고건수·고령인구·산식과 기사 문장이 일치하는지 검사.
'고령인구 1만 명당 사고건수'는 발생지 사고건수 ÷ 거주지 고령인구 × 10000으로 계산하는
기술통계 지표이다. 발생지/거주지 기준이 다르다는 이유만으로 산식 오류나 허위 수치로 판정하지 말라.
단, 실제 고령층 보행 노출량을 보정한 위험률·개인 사고 확률·인과 효과로 해석하면 오류다.
본문에 수치가 Fact Sheet와 맞고 '고령인구 1만 명당'이라고 정확히 표시했다면 오검출 금지.
[다른 검수]
사고다발지역 폴리곤 수와 개별 사고 건수의 혼동, 보호구역 API 누락 무시 확인.
근거 없는 인과·효과·정책 시행·현장 취재·인터뷰·출처 주장을 확인.
METADATA_ONLY는 근거가 아님. VERIFIED의 대조된 원문 발췌만 외부 사실 근거.
칭찬·문체 취향·추정 오류 제외. 동일 오류 중복 지적하지 말 것.
오류 구절을 기사에서 정확히 발췌하고, 해당 Fact Sheet와 충돌하는 이유를 특정하라.
기사는 수정하지 말 것."""

def ai_findings(a):
    if not os.getenv("OPENAI_API_KEY"):raise RuntimeError("OPENAI_API_KEY 없음")
    evidence=[e["payload"] for e in a["evidence"] if e["payload"]]
    request={"today_kst":datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
             "title":a["title"],"content":a["content"],"evidence":evidence}
    response=OpenAI(api_key=os.environ["OPENAI_API_KEY"],timeout=40,max_retries=0).responses.parse(
        model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),instructions=PROMPT,
        input=json.dumps(request,ensure_ascii=False,default=str),text_format=Review)
    if response.output_parsed is None:raise RuntimeError("AI 검수 응답 오류")
    body=a["title"]+"\n"+a["content"]
    return [f.model_dump() for f in response.output_parsed.findings if f.excerpt.strip() in body and f.excerpt.strip()]

def validate(engine,id):
    with engine.connect() as conn:a=context(conn,id)
    if a["status"]!="검토대기":raise ValueError("검토대기 기사만 검수")
    problems=grounding(a)
    if not problems:problems=numeric(a)+ai_findings(a) # AI 오류는 PASS로 저장하지 않음
    h=digest(a)
    result={"passed":not problems,"issues":problems,"content_hash":h,"checked_at":datetime.now(timezone.utc).isoformat()}
    with engine.begin() as conn:
        now=context(conn,id,True)
        if now["status"]!="검토대기" or digest(now)!=h:raise ValueError("검수 도중 근거 또는 본문 변경")
        conn.execute(text("""UPDATE articles SET validation_passed=:passed,
            validation_result=:report,validated_hash=:hash,reviewed_by=NULL,
            reviewed_at=NULL,review_note=NULL,published_at=NULL WHERE id=:id"""),
            {"passed":result["passed"],"report":json.dumps(result,ensure_ascii=False),"hash":h,"id":id})
    return result

def editor_password_valid(password):
    try:
        algorithm,it,salt,expected=os.getenv("EDITOR_PASSWORD_HASH","").split(":")
        count=int(it)
        if algorithm!="pbkdf2_sha256" or not 100000<=count<=2000000:return False
        found=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),count)
        return hmac.compare_digest(found,bytes.fromhex(expected))
    except (TypeError,ValueError,OverflowError):return False

def decide(engine,id,reviewer,password,checks,approve,note=""):
    reviewer=reviewer.strip()
    if not reviewer or len(reviewer)>100 or len(checks)!=4:raise ValueError("편집장 이름·체크리스트 확인")
    if not editor_password_valid(password):raise ValueError("편집장 비밀번호 불일치 또는 미설정")
    with engine.begin() as conn:
        a=context(conn,id,True)
        if a["status"]!="검토대기":raise ValueError("검토대기 기사만 결정 가능")
        if approve:
            r=a["validation_result"]; h=digest(a)
            if not all(checks) or grounding(a) or not a["validation_passed"] or not r or not r.get("passed"):
                raise ValueError("체크리스트 4개·자동 검수 PASS·근거 확인 필요")
            if h!=a["validated_hash"] or h!=r.get("content_hash"):
                raise ValueError("검수 이후 기사·근거 변경: 재검수 필요")
        status="승인" if approve else "보류"
        conn.execute(text("""UPDATE articles SET status=:status,reviewed_by=:name,
            reviewed_at=UTC_TIMESTAMP(),review_note=:note,
            published_at=CASE WHEN :approve THEN UTC_TIMESTAMP() ELSE NULL END
            WHERE id=:id"""),
            {"status":status,"name":reviewer,"note":note[:3000],"approve":approve,"id":id})
    return status

def list_articles(engine,only_approved=False):
    with engine.connect() as conn:
        rows=conn.execute(text("""SELECT id,title,status,validation_passed,reviewed_by,published_at
            FROM articles WHERE (:only=FALSE OR status='승인') ORDER BY id DESC LIMIT 100"""),
            {"only":only_approved}).mappings().all()
    return [dict(r) for r in rows]
