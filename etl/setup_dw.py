#!/usr/bin/env python3
"""Construieste schema DW (star schema) si incarca datele din OLTP.

Pornire: python etl/setup_dw.py (dupa setup_oltp.py)
"""
import os
import sys
from datetime import date, timedelta

import oracledb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MONTH_RO = {1:'Ianuarie', 2:'Februarie', 3:'Martie', 4:'Aprilie',
            5:'Mai', 6:'Iunie', 7:'Iulie', 8:'August',
            9:'Septembrie', 10:'Octombrie', 11:'Noiembrie', 12:'Decembrie'}
# Oracle D (NLS_TERRITORY=AMERICA): 1=Duminica, 2=Luni, ..., 7=Sambata
DAY_RO = {1:'Duminica', 2:'Luni', 3:'Marti', 4:'Miercuri',
          5:'Joi', 6:'Vineri', 7:'Sambata'}

def python_dow_to_oracle(weekday):
    """Python weekday: Mon=0..Sun=6 -> Oracle D: Sun=1, Mon=2..Sat=7"""
    return (weekday + 2) % 7 or 7

from config import connect_dw as conn_dw  # noqa: E402
from config import connect_oltp as conn_oltp  # noqa: E402
from config import connect_sys as conn_sys  # noqa: E402

def run_sqls(c, sqls, label=""):
    cur = c.cursor()
    ok = err = 0
    for sql in sqls:
        sql = sql.strip()
        if not sql or sql.startswith('--'):
            continue
        try:
            cur.execute(sql)
            ok += 1
        except Exception as e:
            msg = str(e)
            # Ignora "exista deja" / "nu exista"
            if any(x in msg for x in ['ORA-00955', 'ORA-02289', 'ORA-04043',
                                        'ORA-04080', 'ORA-04044', 'ORA-00942']):
                pass
            else:
                print(f"  ⚠️  [{label}] {msg[:100]}: {sql[:80]}")
                err += 1
    c.commit()
    cur.close()
    return ok, err

def exec_one(c, sql, label=""):
    cur = c.cursor()
    try:
        cur.execute(sql)
        c.commit()
        return True
    except Exception as e:
        print(f"  ⚠️  [{label}] {e}")
        c.rollback()
        return False
    finally:
        cur.close()

print("=" * 60)
print("  Setup DW Clinica Stomatologica")
print("=" * 60)

print("\n[0/11] Verific conexiunea la Oracle XE...")
import time
for attempt in range(20):
    try:
        c = conn_oltp()
        c.close()
        print("  ✅  Oracle XE disponibil!")
        break
    except Exception as e:
        print(f"  Astept Oracle... ({attempt+1}/20): {e}")
        time.sleep(5)
else:
    print("  ❌ Oracle nu e disponibil. Verifica Docker-ul.")
    sys.exit(1)

print("\n[1/11] Corectie OLTP: ISTORIC_MEDICAL inregistrarea 6 (ID_PACIENT 13 -> 10)...")
c = conn_oltp()
cur = c.cursor()
cur.execute("SELECT COUNT(*) FROM ISTORIC_MEDICAL")
cnt = cur.fetchone()[0]
print(f"  ISTORIC_MEDICAL curent: {cnt} randuri")

if cnt < 6:
    try:
        cur.execute("DELETE FROM ISTORIC_MEDICAL WHERE ID_ISTORIC = 6")
    except: pass
    try:
        cur.execute("ALTER TABLE ISTORIC_MEDICAL DISABLE CONSTRAINT FK_IST_PACIENT")
        cur.execute("ALTER TABLE ISTORIC_MEDICAL DISABLE CONSTRAINT FK_IST_MEDIC")
        cur.execute("ALTER TABLE ISTORIC_MEDICAL DISABLE CONSTRAINT FK_IST_PROGRAMARE")
    except: pass
    sql_fix = """INSERT INTO ISTORIC_MEDICAL VALUES (
        6, 10, 4, 13,
        'Dinte 36 cu necroza pulpara. Necesita tratament endodontic.',
        'Tratament canal si coroana de acoperire',
        TO_DATE('2024-07-01','YYYY-MM-DD'), NULL)"""
    try:
        cur.execute(sql_fix)
        c.commit()
        print("  ✅  Inregistrarea 6 inserat cu ID_PACIENT=10")
    except Exception as e:
        print(f"  ⚠️  Inserare esuata: {e}")
    try:
        cur.execute("ALTER TABLE ISTORIC_MEDICAL ENABLE CONSTRAINT FK_IST_PACIENT")
        cur.execute("ALTER TABLE ISTORIC_MEDICAL ENABLE CONSTRAINT FK_IST_MEDIC")
        cur.execute("ALTER TABLE ISTORIC_MEDICAL ENABLE CONSTRAINT FK_IST_PROGRAMARE")
    except Exception as e:
        print(f"  ⚠️  Reactivare FK: {e}")
elif cnt == 6:
    print("  ✅  ISTORIC_MEDICAL are deja 6 randuri - verificare ID_PACIENT...")
    cur.execute("SELECT ID_PACIENT FROM ISTORIC_MEDICAL WHERE ID_ISTORIC = 6")
    row = cur.fetchone()
    if row and row[0] == 13:
        print("  ⚠️  Inregistrarea 6 are ID_PACIENT=13 gresit. Corectez...")
        try:
            cur.execute("UPDATE ISTORIC_MEDICAL SET ID_PACIENT=10 WHERE ID_ISTORIC=6")
            c.commit()
            print("  ✅  Corectat la ID_PACIENT=10")
        except Exception as e:
            print(f"  ⚠️  Actualizare esuata: {e}")
    else:
        print(f"  ✅  Inregistrarea 6 OK (ID_PACIENT={row[0] if row else 'N/A'})")
cur.close()
c.close()

print("\n[2/11] Drepturi: stoma_oltp.* -> stoma_dw (ca SYS)...")
c = conn_sys()
grant_sqls = [
    "GRANT SELECT ON stoma_oltp.PACIENTI TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.MEDICI TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.CABINETE TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.SERVICII TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.PROGRAMARI TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.PROGRAMARI_SERVICII TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.FACTURI TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.MATERIALE TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.ASISTENTE TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.UTILIZARI_MATERIALE TO stoma_dw",
    "GRANT SELECT ON stoma_oltp.ISTORIC_MEDICAL TO stoma_dw",
    "GRANT CREATE DIMENSION TO stoma_dw",
    "GRANT QUERY REWRITE TO stoma_dw",
    "GRANT CREATE MATERIALIZED VIEW TO stoma_dw",
]
cur = c.cursor()
for sql in grant_sqls:
    try:
        cur.execute(sql)
        c.commit()
    except Exception as e:
        if 'ORA-01749' in str(e):  # deja acordat
            pass
        else:
            print(f"  ⚠️  {e}: {sql[:60]}")
cur.close()
c.close()
print("  ✅  Drepturi acordate")

print("\n[3/11] Curatare schema DW (stergere obiecte existente)...")
c = conn_dw()
cur = c.cursor()

for obj in ['MV_VANZARI_LUNARE']:
    try:
        cur.execute(f"DROP MATERIALIZED VIEW {obj}")
        c.commit()
    except: pass

for dim in ['dim_timp_hier', 'dim_servicii_hier', 'dim_pacienti_geo']:
    try:
        cur.execute(f"DROP DIMENSION {dim}")
        c.commit()
    except: pass

for t in ['FAPTE_SERVICII', 'DIM_TIMP', 'DIM_PACIENTI', 'DIM_MEDICI',
          'DIM_SERVICII', 'DIM_CABINETE', 'DIM_LOCATIE', 'DIM_METODA_PLATA']:
    try:
        cur.execute(f"DROP TABLE {t} CASCADE CONSTRAINTS")
        c.commit()
    except: pass

for s in ['seq_dw_pacienti', 'seq_dw_medici', 'seq_dw_servicii',
          'seq_dw_cabinete', 'seq_dw_locatie', 'seq_dw_fapte']:
    try:
        cur.execute(f"DROP SEQUENCE {s}")
        c.commit()
    except: pass

cur.close()
c.close()
print("  ✅  Schema DW curatata")

print("\n[4/11] Creare tabele dimensiune si tabel fapte...")
c = conn_dw()
ddl_sqls = [
    """CREATE TABLE DIM_TIMP (
      ID_TIMP          DATE          NOT NULL,
      AN               NUMBER(4)     NOT NULL,
      SEMESTRU         NUMBER(1)     NOT NULL,
      TRIMESTRU        NUMBER(1)     NOT NULL,
      LUNA             NUMBER(2)     NOT NULL,
      LUNA_NUME        VARCHAR2(20)  NOT NULL,
      SAPTAMANA_AN     NUMBER(2)     NOT NULL,
      ZI               NUMBER(2)     NOT NULL,
      ZI_SAPTAMANA     NUMBER(1)     NOT NULL,
      ZI_NUME          VARCHAR2(20)  NOT NULL,
      WEEKEND          NUMBER(1)     DEFAULT 0,
      CONSTRAINT PK_DIM_TIMP PRIMARY KEY (ID_TIMP)
    )""",
    "ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_LUNA   CHECK (LUNA BETWEEN 1 AND 12)",
    "ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_ZI     CHECK (ZI   BETWEEN 1 AND 31)",
    "ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_WEEK   CHECK (WEEKEND IN (0,1))",
    "ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_TRIM   CHECK (TRIMESTRU BETWEEN 1 AND 4)",
    "ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_SEM    CHECK (SEMESTRU  IN (1, 2))",
    """CREATE TABLE DIM_PACIENTI (
      ID_PACIENT_DW    NUMBER(6)     NOT NULL,
      ID_PACIENT_OLTP  NUMBER(6)     NOT NULL,
      NUME             VARCHAR2(50)  NOT NULL,
      PRENUME          VARCHAR2(50)  NOT NULL,
      ORAS             VARCHAR2(50),
      JUDET            VARCHAR2(50),
      GRUPA_VARSTA     VARCHAR2(20),
      DATA_INREG       DATE,
      ACTIV            CHAR(1)       DEFAULT 'Y',
      DATA_START       DATE          DEFAULT SYSDATE,
      DATA_SFARSIT     DATE,
      CONSTRAINT PK_DIM_PACIENTI PRIMARY KEY (ID_PACIENT_DW)
    )""",
    "CREATE SEQUENCE seq_dw_pacienti START WITH 1 INCREMENT BY 1 NOCACHE",
    """CREATE TABLE DIM_MEDICI (
      ID_MEDIC_DW     NUMBER(4)     NOT NULL,
      ID_MEDIC_OLTP   NUMBER(4)     NOT NULL,
      NUME            VARCHAR2(50)  NOT NULL,
      PRENUME         VARCHAR2(50)  NOT NULL,
      SPECIALIZARE    VARCHAR2(80)  NOT NULL,
      ACTIV           CHAR(1)       DEFAULT 'Y',
      CONSTRAINT PK_DIM_MEDICI PRIMARY KEY (ID_MEDIC_DW)
    )""",
    "CREATE SEQUENCE seq_dw_medici START WITH 1 INCREMENT BY 1 NOCACHE",
    """CREATE TABLE DIM_SERVICII (
      ID_SERVICIU_DW   NUMBER(4)     NOT NULL,
      ID_SERVICIU_OLTP NUMBER(4)     NOT NULL,
      DENUMIRE         VARCHAR2(100) NOT NULL,
      CATEGORIE        VARCHAR2(50)  NOT NULL,
      SUBCATEGORIE     VARCHAR2(80),
      PRET_LISTA       NUMBER(10,2),
      DURATA_MIN       NUMBER(4),
      ACTIV            CHAR(1)       DEFAULT 'Y',
      CONSTRAINT PK_DIM_SERVICII PRIMARY KEY (ID_SERVICIU_DW)
    )""",
    "CREATE SEQUENCE seq_dw_servicii START WITH 1 INCREMENT BY 1 NOCACHE",
    """CREATE TABLE DIM_CABINETE (
      ID_CABINET_DW   NUMBER(4)     NOT NULL,
      ID_CABINET_OLTP NUMBER(4)     NOT NULL,
      DENUMIRE        VARCHAR2(50)  NOT NULL,
      ETAJ            NUMBER(2),
      TIP_CABINET     VARCHAR2(50),
      ACTIV           CHAR(1)       DEFAULT 'Y',
      CONSTRAINT PK_DIM_CABINETE PRIMARY KEY (ID_CABINET_DW)
    )""",
    "CREATE SEQUENCE seq_dw_cabinete START WITH 1 INCREMENT BY 1 NOCACHE",
    """CREATE TABLE DIM_LOCATIE (
      ID_LOCATIE NUMBER(6)    NOT NULL,
      ORAS       VARCHAR2(50) NOT NULL,
      JUDET      VARCHAR2(50),
      REGIUNE    VARCHAR2(50),
      CONSTRAINT PK_DIM_LOCATIE PRIMARY KEY (ID_LOCATIE)
    )""",
    "CREATE SEQUENCE seq_dw_locatie START WITH 1 INCREMENT BY 1 NOCACHE",
    """CREATE TABLE DIM_METODA_PLATA (
      ID_METODA   NUMBER(4)     NOT NULL,
      DENUMIRE    VARCHAR2(30)  NOT NULL,
      TIP         VARCHAR2(20),
      CONSTRAINT PK_DIM_METODA PRIMARY KEY (ID_METODA)
    )""",

    """CREATE TABLE FAPTE_SERVICII (
      ID_FAPT          NUMBER(10)    NOT NULL,
      TIMP_ID          DATE          NOT NULL,
      PACIENT_ID       NUMBER(6)     NOT NULL,
      MEDIC_ID         NUMBER(4)     NOT NULL,
      SERVICIU_ID      NUMBER(4)     NOT NULL,
      CABINET_ID       NUMBER(4)     NOT NULL,
      LOCATIE_ID       NUMBER(6)     NOT NULL,
      METODA_PLATA_ID  NUMBER(4),
      ID_PROGRAMARE_OLTP NUMBER(6),
      ID_FACTURA_OLTP    NUMBER(8),
      CANTITATE          NUMBER(4)   DEFAULT 1,
      PRET_UNITAR        NUMBER(10,2),
      DISCOUNT_PROC      NUMBER(5,2) DEFAULT 0,
      SUBTOTAL_FARA_TVA  NUMBER(10,2),
      SUMA_TVA           NUMBER(10,2),
      TOTAL_CU_TVA       NUMBER(10,2),
      SUMA_PLATITA       NUMBER(10,2),
      CONSTRAINT PK_FAPTE_SERVICII PRIMARY KEY (ID_FAPT, TIMP_ID)
    )
    PARTITION BY RANGE (TIMP_ID) (
      PARTITION p_2023 VALUES LESS THAN (TO_DATE('2024-01-01','YYYY-MM-DD')),
      PARTITION p_2024 VALUES LESS THAN (TO_DATE('2025-01-01','YYYY-MM-DD')),
      PARTITION p_2025 VALUES LESS THAN (TO_DATE('2026-01-01','YYYY-MM-DD')),
      PARTITION p_viitor VALUES LESS THAN (MAXVALUE)
    )""",
    "CREATE SEQUENCE seq_dw_fapte START WITH 1 INCREMENT BY 1 NOCACHE",
    "ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_CANT    CHECK (CANTITATE > 0)",
    "ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_SUBTOT  CHECK (SUBTOTAL_FARA_TVA >= 0)",
    "ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_TVA     CHECK (SUMA_TVA >= 0)",
    "ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_TOTAL   CHECK (TOTAL_CU_TVA >= 0)",
    "ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_DISC    CHECK (DISCOUNT_PROC BETWEEN 0 AND 100)",
]

cur = c.cursor()
for sql in ddl_sqls:
    sql = sql.strip()
    try:
        cur.execute(sql)
        c.commit()
    except Exception as e:
        print(f"  ⚠️  Eroare DDL: {e}: {sql[:60]}")
cur.close()
c.close()
print("  ✅  Tabele DW create")

print("\n[5/11] Populare DIM_TIMP (2023-01-01 -> 2025-12-31, 1096 zile)...")
c = conn_dw()
cur = c.cursor()
start_date = date(2023, 1, 1)
rows = []
for d in range(1096):
    dt = start_date + timedelta(days=d)
    an     = dt.year
    luna   = dt.month
    zi     = dt.day
    trim   = (luna - 1) // 3 + 1
    sem    = 1 if luna <= 6 else 2
    iso_w  = dt.isocalendar()[1]
    oracle_d = python_dow_to_oracle(dt.weekday())
    weekend = 1 if oracle_d in (1, 7) else 0
    rows.append((
        dt,
        an,
        sem,
        trim,
        luna,
        MONTH_RO[luna],
        iso_w,
        zi,
        oracle_d,
        DAY_RO[oracle_d],
        weekend
    ))

cur.executemany(
    """INSERT INTO DIM_TIMP (ID_TIMP, AN, SEMESTRU, TRIMESTRU, LUNA, LUNA_NUME,
       SAPTAMANA_AN, ZI, ZI_SAPTAMANA, ZI_NUME, WEEKEND)
       VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11)""",
    rows
)
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_TIMP")
cnt = cur.fetchone()[0]
cur.close()
c.close()
print(f"  ✅  DIM_TIMP: {cnt} randuri inserate")

print("\n[6/11] Populare dimensiuni din OLTP...")
c = conn_dw()
cur = c.cursor()
cur.execute("""
INSERT INTO DIM_PACIENTI (
  ID_PACIENT_DW, ID_PACIENT_OLTP, NUME, PRENUME, ORAS, JUDET,
  GRUPA_VARSTA, DATA_INREG, ACTIV, DATA_START
)
SELECT
  seq_dw_pacienti.NEXTVAL,
  p.ID_PACIENT,
  p.NUME,
  p.PRENUME,
  p.ORAS,
  p.JUDET,
  CASE
    WHEN TRUNC((SYSDATE - p.DATA_NASTERII)/365) < 18 THEN '0-17'
    WHEN TRUNC((SYSDATE - p.DATA_NASTERII)/365) < 30 THEN '18-29'
    WHEN TRUNC((SYSDATE - p.DATA_NASTERII)/365) < 45 THEN '30-44'
    WHEN TRUNC((SYSDATE - p.DATA_NASTERII)/365) < 60 THEN '45-59'
    ELSE '60+'
  END,
  p.DATA_INREGISTRARII,
  p.ACTIV,
  SYSDATE
FROM stoma_oltp.PACIENTI p
""")
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_PACIENTI")
print(f"  DIM_PACIENTI: {cur.fetchone()[0]} randuri")
cur.execute("""
INSERT INTO DIM_MEDICI (ID_MEDIC_DW, ID_MEDIC_OLTP, NUME, PRENUME, SPECIALIZARE, ACTIV)
SELECT seq_dw_medici.NEXTVAL, m.ID_MEDIC, m.NUME, m.PRENUME, m.SPECIALIZARE, m.ACTIV
FROM stoma_oltp.MEDICI m
""")
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_MEDICI")
print(f"  DIM_MEDICI: {cur.fetchone()[0]} randuri")
cur.execute("""
INSERT INTO DIM_SERVICII (
  ID_SERVICIU_DW, ID_SERVICIU_OLTP, DENUMIRE, CATEGORIE, SUBCATEGORIE,
  PRET_LISTA, DURATA_MIN, ACTIV
)
SELECT
  seq_dw_servicii.NEXTVAL,
  s.ID_SERVICIU,
  s.DENUMIRE,
  s.CATEGORIE,
  CASE s.CATEGORIE
    WHEN 'Preventie'     THEN 'Igienizare si profilaxie'
    WHEN 'Restauratoare' THEN 'Obturatii si reconstructii'
    WHEN 'Endodontie'    THEN 'Tratamente de canal'
    WHEN 'Chirurgie'     THEN 'Extractii si interventii'
    WHEN 'Ortodontie'    THEN 'Corectii ocluzale'
    WHEN 'Estetica'      THEN 'Albiri si fatete'
    WHEN 'Protetica'     THEN 'Coroane si proteze'
    WHEN 'Radiologie'    THEN 'Imagistica'
    ELSE 'Altele'
  END,
  s.PRET,
  s.DURATA_MIN,
  s.ACTIV
FROM stoma_oltp.SERVICII s
""")
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_SERVICII")
print(f"  DIM_SERVICII: {cur.fetchone()[0]} randuri")
cur.execute("""
INSERT INTO DIM_CABINETE (ID_CABINET_DW, ID_CABINET_OLTP, DENUMIRE, ETAJ, TIP_CABINET, ACTIV)
SELECT
  seq_dw_cabinete.NEXTVAL,
  c.ID_CABINET,
  c.DENUMIRE,
  c.ETAJ,
  CASE
    WHEN LOWER(c.DENUMIRE) LIKE '%radiologie%' THEN 'Radiologie'
    WHEN LOWER(c.DENUMIRE) LIKE '%chirurgie%'  THEN 'Chirurgie'
    WHEN LOWER(c.DENUMIRE) LIKE '%ortodont%'   THEN 'Ortodontie'
    WHEN LOWER(c.DENUMIRE) LIKE '%estetica%'   THEN 'Estetica'
    ELSE 'General'
  END,
  c.ACTIV
FROM stoma_oltp.CABINETE c
""")
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_CABINETE")
print(f"  DIM_CABINETE: {cur.fetchone()[0]} randuri")
cur.execute("""
INSERT INTO DIM_LOCATIE (ID_LOCATIE, ORAS, JUDET, REGIUNE)
SELECT
  seq_dw_locatie.NEXTVAL,
  oras,
  judet,
  CASE judet
    WHEN 'Ilfov'    THEN 'Muntenia'
    WHEN 'Cluj'     THEN 'Transilvania'
    WHEN 'Brasov'   THEN 'Transilvania'
    WHEN 'Iasi'     THEN 'Moldova'
    WHEN 'Timis'    THEN 'Banat'
    ELSE 'Alte'
  END
FROM (
  SELECT DISTINCT ORAS, JUDET
  FROM stoma_oltp.PACIENTI
  WHERE ORAS IS NOT NULL
)
""")
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_LOCATIE")
print(f"  DIM_LOCATIE: {cur.fetchone()[0]} randuri")
for row in [(1,'Cash','Numerar'),(2,'Card','Electronic'),
            (3,'Transfer','Electronic'),(4,'Asigurare','Tert platitor'),
            (0,'Necunoscut','N/A')]:
    cur.execute("INSERT INTO DIM_METODA_PLATA VALUES (:1,:2,:3)", row)
c.commit()
cur.execute("SELECT COUNT(*) FROM DIM_METODA_PLATA")
print(f"  DIM_METODA_PLATA: {cur.fetchone()[0]} randuri")

cur.close()
c.close()
print("  ✅  Dimensiuni populate")

print("\n[7/11] ETL: Populare FAPTE_SERVICII din OLTP...")
c = conn_dw()
cur = c.cursor()

etl_sql = """
INSERT INTO FAPTE_SERVICII (
  ID_FAPT, TIMP_ID, PACIENT_ID, MEDIC_ID, SERVICIU_ID,
  CABINET_ID, LOCATIE_ID, METODA_PLATA_ID,
  ID_PROGRAMARE_OLTP, ID_FACTURA_OLTP,
  CANTITATE, PRET_UNITAR, DISCOUNT_PROC,
  SUBTOTAL_FARA_TVA, SUMA_TVA, TOTAL_CU_TVA, SUMA_PLATITA
)
SELECT
  seq_dw_fapte.NEXTVAL,
  TRUNC(pr.DATA_PROG),
  dp.ID_PACIENT_DW,
  dm.ID_MEDIC_DW,
  ds.ID_SERVICIU_DW,
  dc.ID_CABINET_DW,
  NVL(dl.ID_LOCATIE, 1),
  NVL(
    (SELECT ID_METODA FROM DIM_METODA_PLATA
     WHERE DENUMIRE = f.METODA_PLATA), 0),
  pr.ID_PROGRAMARE,
  f.ID_FACTURA,
  ps.CANTITATE,
  ps.PRET_APLICAT,
  ps.DISCOUNT_PROC,
  ROUND(ps.CANTITATE * ps.PRET_APLICAT * (1 - ps.DISCOUNT_PROC/100), 2),
  ROUND(ps.CANTITATE * ps.PRET_APLICAT * (1 - ps.DISCOUNT_PROC/100) * 0.19, 2),
  ROUND(ps.CANTITATE * ps.PRET_APLICAT * (1 - ps.DISCOUNT_PROC/100) * 1.19, 2),
  NVL(f.SUMA_PLATITA / NULLIF(
      (SELECT COUNT(*) FROM stoma_oltp.PROGRAMARI_SERVICII ps2
       WHERE ps2.ID_PROGRAMARE = pr.ID_PROGRAMARE), 0), 0)
FROM
  stoma_oltp.PROGRAMARI_SERVICII ps
  JOIN stoma_oltp.PROGRAMARI  pr ON pr.ID_PROGRAMARE = ps.ID_PROGRAMARE
  JOIN stoma_oltp.FACTURI     f  ON f.ID_PROGRAMARE  = pr.ID_PROGRAMARE
  JOIN DIM_PACIENTI           dp ON dp.ID_PACIENT_OLTP = pr.ID_PACIENT
  JOIN DIM_MEDICI             dm ON dm.ID_MEDIC_OLTP   = pr.ID_MEDIC
  JOIN DIM_SERVICII           ds ON ds.ID_SERVICIU_OLTP = ps.ID_SERVICIU
  JOIN DIM_CABINETE           dc ON dc.ID_CABINET_OLTP = pr.ID_CABINET
  LEFT JOIN stoma_oltp.PACIENTI pac ON pac.ID_PACIENT = pr.ID_PACIENT
  LEFT JOIN DIM_LOCATIE dl ON dl.ORAS = pac.ORAS AND dl.JUDET = pac.JUDET
WHERE pr.STATUS = 'Finalizata'
"""
try:
    cur.execute(etl_sql)
    c.commit()
    cur.execute("SELECT COUNT(*) FROM FAPTE_SERVICII")
    cnt_fact = cur.fetchone()[0]
    print(f"  ✅  FAPTE_SERVICII: {cnt_fact} randuri inserate")
except Exception as e:
    print(f"  ❌  Eroare ETL: {e}")

cur.close()
c.close()

print("\n[8/11] Adaug FK constraints (DEFERRABLE INITIALLY DEFERRED)...")
c = conn_dw()
fk_sqls = [
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_TIMP
       FOREIGN KEY (TIMP_ID) REFERENCES DIM_TIMP(ID_TIMP)
       DEFERRABLE INITIALLY DEFERRED""",
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_PACIENT
       FOREIGN KEY (PACIENT_ID) REFERENCES DIM_PACIENTI(ID_PACIENT_DW)
       DEFERRABLE INITIALLY DEFERRED""",
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_MEDIC
       FOREIGN KEY (MEDIC_ID) REFERENCES DIM_MEDICI(ID_MEDIC_DW)
       DEFERRABLE INITIALLY DEFERRED""",
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_SERVICIU
       FOREIGN KEY (SERVICIU_ID) REFERENCES DIM_SERVICII(ID_SERVICIU_DW)
       DEFERRABLE INITIALLY DEFERRED""",
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_CABINET
       FOREIGN KEY (CABINET_ID) REFERENCES DIM_CABINETE(ID_CABINET_DW)
       DEFERRABLE INITIALLY DEFERRED""",
    """ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_LOCATIE
       FOREIGN KEY (LOCATIE_ID) REFERENCES DIM_LOCATIE(ID_LOCATIE)
       DEFERRABLE INITIALLY DEFERRED""",
]
cur = c.cursor()
ok = 0
for sql in fk_sqls:
    try:
        cur.execute(sql.strip())
        c.commit()
        ok += 1
    except Exception as e:
        print(f"  ⚠️  FK: {e}")
cur.close()
c.close()
print(f"  ✅  {ok}/{len(fk_sqls)} FK constraints adaugate")

print("\n[9/11] Creare indecsi (Bitmap LOCAL + B-Tree)...")
c = conn_dw()
idx_sqls = [
    # Bitmap LOCAL pe FK-urile din fact (cardinalitate mica)
    "CREATE BITMAP INDEX idx_fapt_medic_bm    ON FAPTE_SERVICII(MEDIC_ID) LOCAL",
    "CREATE BITMAP INDEX idx_fapt_serviciu_bm ON FAPTE_SERVICII(SERVICIU_ID) LOCAL",
    "CREATE BITMAP INDEX idx_fapt_cabinet_bm  ON FAPTE_SERVICII(CABINET_ID) LOCAL",
    "CREATE BITMAP INDEX idx_fapt_locatie_bm  ON FAPTE_SERVICII(LOCATIE_ID) LOCAL",
    "CREATE BITMAP INDEX idx_fapt_metoda_bm   ON FAPTE_SERVICII(METODA_PLATA_ID) LOCAL",
    # B-Tree LOCAL pe coloane de filtrare
    "CREATE INDEX idx_fapt_timp      ON FAPTE_SERVICII(TIMP_ID) LOCAL",
    "CREATE INDEX idx_fapt_pacient   ON FAPTE_SERVICII(PACIENT_ID) LOCAL",
    # B-Tree pe dimensiuni
    "CREATE INDEX idx_dim_timp_an_luna ON DIM_TIMP(AN, LUNA, ID_TIMP)",
    "CREATE INDEX idx_dim_medic_spec   ON DIM_MEDICI(SPECIALIZARE)",
    "CREATE INDEX idx_dim_serv_cat     ON DIM_SERVICII(CATEGORIE)",
]
cur = c.cursor()
ok = 0
for sql in idx_sqls:
    try:
        cur.execute(sql.strip())
        c.commit()
        ok += 1
    except Exception as e:
        print(f"  ⚠️  Index: {e}")
cur.close()
c.close()
print(f"  ✅  {ok}/{len(idx_sqls)} indecsi creati")

print("\n[10/11] Creare obiecte DIMENSION...")
c = conn_dw()
dim_sqls = [
    """CREATE DIMENSION dim_timp_hier
       LEVEL zi        IS DIM_TIMP.ID_TIMP
       LEVEL luna      IS DIM_TIMP.LUNA
       LEVEL trimestru IS DIM_TIMP.TRIMESTRU
       LEVEL an        IS DIM_TIMP.AN
       HIERARCHY timp_roll_up (
         zi CHILD OF luna
         CHILD OF trimestru
         CHILD OF an
       )
       ATTRIBUTE zi       DETERMINES (DIM_TIMP.ZI_NUME, DIM_TIMP.ZI_SAPTAMANA,
                                      DIM_TIMP.WEEKEND, DIM_TIMP.SAPTAMANA_AN)
       ATTRIBUTE luna     DETERMINES DIM_TIMP.LUNA_NUME
       ATTRIBUTE trimestru DETERMINES DIM_TIMP.SEMESTRU""",

    """CREATE DIMENSION dim_servicii_hier
       LEVEL serviciu    IS DIM_SERVICII.ID_SERVICIU_DW
       LEVEL subcategorie IS DIM_SERVICII.SUBCATEGORIE
       LEVEL categorie   IS DIM_SERVICII.CATEGORIE
       HIERARCHY serv_roll_up (
         serviciu    CHILD OF subcategorie
         CHILD OF categorie
       )
       ATTRIBUTE serviciu  DETERMINES (DIM_SERVICII.DENUMIRE, DIM_SERVICII.PRET_LISTA,
                                       DIM_SERVICII.DURATA_MIN)
       ATTRIBUTE categorie DETERMINES DIM_SERVICII.CATEGORIE""",

    """CREATE DIMENSION dim_pacienti_geo
       LEVEL pacient IS DIM_PACIENTI.ID_PACIENT_DW
       LEVEL oras    IS DIM_PACIENTI.ORAS
       LEVEL judet   IS DIM_PACIENTI.JUDET
       HIERARCHY geo_roll_up (
         pacient CHILD OF oras
         CHILD OF judet
       )
       ATTRIBUTE pacient DETERMINES (DIM_PACIENTI.NUME, DIM_PACIENTI.PRENUME,
                                     DIM_PACIENTI.GRUPA_VARSTA)""",
]
cur = c.cursor()
ok = 0
for sql in dim_sqls:
    try:
        cur.execute(sql.strip())
        c.commit()
        ok += 1
    except Exception as e:
        print(f"  ⚠️  DIMENSION: {e}")
cur.close()
c.close()
print(f"  ✅  {ok}/{len(dim_sqls)} obiecte DIMENSION create")

print("\n[11/11] Creare Materialized View MV_VANZARI_LUNARE...")
c = conn_dw()
mv_sql = """
CREATE MATERIALIZED VIEW MV_VANZARI_LUNARE
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT
  t.AN,
  t.TRIMESTRU,
  t.LUNA,
  t.LUNA_NUME,
  s.CATEGORIE,
  m.SPECIALIZARE,
  m.NUME    AS MEDIC_NUME,
  m.PRENUME AS MEDIC_PRENUME,
  l.ORAS,
  l.JUDET,
  COUNT(f.ID_FAPT)                       AS NR_SERVICII,
  COUNT(DISTINCT f.ID_PROGRAMARE_OLTP)   AS NR_PROGRAMARI,
  COUNT(DISTINCT f.PACIENT_ID)           AS NR_PACIENTI_UNICI,
  SUM(f.CANTITATE)                       AS TOTAL_CANTITATE,
  SUM(f.SUBTOTAL_FARA_TVA)               AS TOTAL_FARA_TVA,
  SUM(f.SUMA_TVA)                        AS TOTAL_TVA,
  SUM(f.TOTAL_CU_TVA)                    AS TOTAL_CU_TVA,
  SUM(f.SUMA_PLATITA)                    AS TOTAL_INCASAT,
  ROUND(AVG(f.PRET_UNITAR), 2)           AS PRET_MEDIU_SERVICIU
FROM
  FAPTE_SERVICII   f
  JOIN DIM_TIMP     t ON t.ID_TIMP        = f.TIMP_ID
  JOIN DIM_SERVICII s ON s.ID_SERVICIU_DW = f.SERVICIU_ID
  JOIN DIM_MEDICI   m ON m.ID_MEDIC_DW    = f.MEDIC_ID
  JOIN DIM_LOCATIE  l ON l.ID_LOCATIE     = f.LOCATIE_ID
GROUP BY
  t.AN, t.TRIMESTRU, t.LUNA, t.LUNA_NUME,
  s.CATEGORIE, m.SPECIALIZARE,
  m.NUME, m.PRENUME, l.ORAS, l.JUDET
"""
cur = c.cursor()
try:
    cur.execute(mv_sql.strip())
    c.commit()
    cur.execute("SELECT COUNT(*) FROM MV_VANZARI_LUNARE")
    print(f"  ✅  MV_VANZARI_LUNARE creata cu {cur.fetchone()[0]} randuri")
except Exception as e:
    print(f"  ⚠️  Eroare MV: {e}")
cur.close()
c.close()

print("\n" + "=" * 60)
print("  VERIFICARE FINALA")
print("=" * 60)

c_oltp = conn_oltp()
c_dw   = conn_dw()
cur_oltp = c_oltp.cursor()
cur_dw   = c_dw.cursor()

print("\n--- OLTP ---")
expected_oltp = {
    "CABINETE":5, "MEDICI":5, "ASISTENTE":3, "PACIENTI":10, "SERVICII":18,
    "MATERIALE":10, "PROGRAMARI":35, "PROGRAMARI_SERVICII":39,
    "FACTURI":33, "UTILIZARI_MATERIALE":11, "ISTORIC_MEDICAL":6
}
all_ok = True
for t, exp in expected_oltp.items():
    cur_oltp.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur_oltp.fetchone()[0]
    status = "✅" if cnt == exp else f"❌ (asteptat {exp})"
    print(f"  {t}: {cnt} {status}")
    if cnt != exp: all_ok = False

print("\n--- DW ---")
dw_tables = [
    ("DIM_TIMP", 1096), ("DIM_PACIENTI", 10), ("DIM_MEDICI", 5),
    ("DIM_SERVICII", 18), ("DIM_CABINETE", 5), ("DIM_LOCATIE", None),
    ("DIM_METODA_PLATA", 5), ("FAPTE_SERVICII", None), ("MV_VANZARI_LUNARE", None)
]
for t, exp in dw_tables:
    try:
        cur_dw.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur_dw.fetchone()[0]
        if exp is not None:
            status = "✅" if cnt == exp else f"⚠️  (asteptat {exp})"
        else:
            status = "✅" if cnt > 0 else "❌ GOOL"
        print(f"  {t}: {cnt} {status}")
    except Exception as e:
        print(f"  {t}: ❌ {e}")

print("\n--- PARTITII FAPTE_SERVICII ---")
try:
    cur_dw.execute("""
        SELECT PARTITION_NAME, NUM_ROWS
        FROM USER_TAB_PARTITIONS
        WHERE TABLE_NAME = 'FAPTE_SERVICII'
        ORDER BY PARTITION_POSITION
    """)
    rows = cur_dw.fetchall()
    if rows:
        for part, nrows in rows:
            print(f"  {part}: {nrows} randuri (statistici necolectate, numar aproximativ)")
    else:
        print("  (fara informatii despre partitii - ruleaza DBMS_STATS.GATHER_TABLE_STATS)")
except Exception as e:
    print(f"  ⚠️  {e}")

cur_oltp.close()
cur_dw.close()
c_oltp.close()
c_dw.close()

print("\n" + "=" * 60)
if all_ok:
    print("  ✅  OLTP PERFECT! DW setup complet!")
else:
    print("  ⚠️  Unele tabele OLTP au date incomplete")
print("=" * 60)
print("\n  Urmatorul pas: ruleaza Flask app:")
print("  python app/app.py")
print("=" * 60)
