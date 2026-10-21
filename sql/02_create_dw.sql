-- Proiect DW & BI - Clinica Stomatologica

-- PASUL 1: Creare utilizator DW (Cerinta Back-End 3)
/*
CREATE USER stoma_dw IDENTIFIED BY dw123;

GRANT UNLIMITED TABLESPACE TO stoma_dw;
GRANT CONNECT, RESOURCE TO stoma_dw;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE,
      CREATE TRIGGER, CREATE MATERIALIZED VIEW,
      CREATE DIMENSION, CREATE VIEW TO stoma_dw;

GRANT SELECT ON stoma_oltp.PACIENTI             TO stoma_dw;
GRANT SELECT ON stoma_oltp.MEDICI               TO stoma_dw;
GRANT SELECT ON stoma_oltp.CABINETE             TO stoma_dw;
GRANT SELECT ON stoma_oltp.SERVICII             TO stoma_dw;
GRANT SELECT ON stoma_oltp.PROGRAMARI           TO stoma_dw;
GRANT SELECT ON stoma_oltp.PROGRAMARI_SERVICII  TO stoma_dw;
GRANT SELECT ON stoma_oltp.FACTURI              TO stoma_dw;
GRANT SELECT ON stoma_oltp.MATERIALE            TO stoma_dw;
*/

-- PASUL 2: Conecteaza-te ca stoma_dw / dw123, apoi ruleaza restul

-- Curatare schema (rulare idempotenta)
BEGIN
  FOR t IN (SELECT table_name FROM user_tables) LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS';
  END LOOP;
  FOR s IN (SELECT sequence_name FROM user_sequences) LOOP
    EXECUTE IMMEDIATE 'DROP SEQUENCE ' || s.sequence_name;
  END LOOP;
END;
/

-- Tabele dimensiune (Cerinta Back-End 3)

-- DIM_TIMP: cand a avut loc serviciul
CREATE TABLE DIM_TIMP (
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
);

-- DIM_PACIENTI: cine a primit serviciul?
CREATE TABLE DIM_PACIENTI (
  ID_PACIENT_DW    NUMBER(6)     NOT NULL,  -- cheie surrogate (generata de noi)
  ID_PACIENT_OLTP  NUMBER(6)     NOT NULL,  -- referinta la OLTP (pentru ETL)
  NUME             VARCHAR2(50)  NOT NULL,
  PRENUME          VARCHAR2(50)  NOT NULL,
  ORAS             VARCHAR2(50),
  JUDET            VARCHAR2(50),
  GRUPA_VARSTA     VARCHAR2(20),
  DATA_INREG       DATE,
  ACTIV            CHAR(1)       DEFAULT 'Y',
  DATA_START       DATE          DEFAULT SYSDATE,  -- SCD Tip 2: de cand e valida inregistrarea
  DATA_SFARSIT     DATE,                           -- SCD Tip 2: pana cand (NULL = curenta)
  CONSTRAINT PK_DIM_PACIENTI PRIMARY KEY (ID_PACIENT_DW)
);

-- Secventa pentru cheia surrogate a pacientilor
CREATE SEQUENCE seq_dw_pacienti START WITH 1 INCREMENT BY 1 NOCACHE;

-- DIM_MEDICI: cine a efectuat serviciul?
CREATE TABLE DIM_MEDICI (
  ID_MEDIC_DW     NUMBER(4)     NOT NULL,  -- cheie surrogate
  ID_MEDIC_OLTP   NUMBER(4)     NOT NULL,  -- referinta la OLTP
  NUME            VARCHAR2(50)  NOT NULL,
  PRENUME         VARCHAR2(50)  NOT NULL,
  SPECIALIZARE    VARCHAR2(80)  NOT NULL,
  ACTIV           CHAR(1)       DEFAULT 'Y',
  CONSTRAINT PK_DIM_MEDICI PRIMARY KEY (ID_MEDIC_DW)
);

CREATE SEQUENCE seq_dw_medici START WITH 1 INCREMENT BY 1 NOCACHE;

-- DIM_SERVICII: ce serviciu s-a efectuat?
CREATE TABLE DIM_SERVICII (
  ID_SERVICIU_DW   NUMBER(4)     NOT NULL,
  ID_SERVICIU_OLTP NUMBER(4)     NOT NULL,
  DENUMIRE         VARCHAR2(100) NOT NULL,
  CATEGORIE        VARCHAR2(50)  NOT NULL,
  SUBCATEGORIE     VARCHAR2(80),
  PRET_LISTA       NUMBER(10,2),
  DURATA_MIN       NUMBER(4),
  ACTIV            CHAR(1)       DEFAULT 'Y',
  CONSTRAINT PK_DIM_SERVICII PRIMARY KEY (ID_SERVICIU_DW)
);

CREATE SEQUENCE seq_dw_servicii START WITH 1 INCREMENT BY 1 NOCACHE;

-- DIM_CABINETE: unde s-a efectuat serviciul? (incaperea fizica)
CREATE TABLE DIM_CABINETE (
  ID_CABINET_DW   NUMBER(4)     NOT NULL,
  ID_CABINET_OLTP NUMBER(4)     NOT NULL,
  DENUMIRE        VARCHAR2(50)  NOT NULL,
  ETAJ            NUMBER(2),
  TIP_CABINET     VARCHAR2(50),
  ACTIV           CHAR(1)       DEFAULT 'Y',
  CONSTRAINT PK_DIM_CABINETE PRIMARY KEY (ID_CABINET_DW)
);

CREATE SEQUENCE seq_dw_cabinete START WITH 1 INCREMENT BY 1 NOCACHE;

-- DIM_LOCATIE: orasul si judetul pacientului
CREATE TABLE DIM_LOCATIE (
  ID_LOCATIE NUMBER(6)    NOT NULL,
  ORAS       VARCHAR2(50) NOT NULL,
  JUDET      VARCHAR2(50),
  REGIUNE    VARCHAR2(50),
  CONSTRAINT PK_DIM_LOCATIE PRIMARY KEY (ID_LOCATIE)
);

CREATE SEQUENCE seq_dw_locatie START WITH 1 INCREMENT BY 1 NOCACHE;

-- DIM_METODA_PLATA: cum s-a platit? (cash, card, transfer, asigurare)
CREATE TABLE DIM_METODA_PLATA (
  ID_METODA   NUMBER(4)     NOT NULL,
  DENUMIRE    VARCHAR2(30)  NOT NULL,
  TIP         VARCHAR2(20),
  CONSTRAINT PK_DIM_METODA PRIMARY KEY (ID_METODA)
);

-- Tabel de fapte (Cerinta Back-End 3)

CREATE TABLE FAPTE_SERVICII (
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
-- Partitionare RANGE pe an (Cerinta Back-End 8)
PARTITION BY RANGE (TIMP_ID) (
  PARTITION p_2023 VALUES LESS THAN (TO_DATE('2024-01-01','YYYY-MM-DD')),
  PARTITION p_2024 VALUES LESS THAN (TO_DATE('2025-01-01','YYYY-MM-DD')),
  PARTITION p_2025 VALUES LESS THAN (TO_DATE('2026-01-01','YYYY-MM-DD')),
  PARTITION p_viitor VALUES LESS THAN (MAXVALUE)
);

-- Secventa pentru ID_FAPT (cheie surrogate a tabelului de fapte)
CREATE SEQUENCE seq_dw_fapte START WITH 1 INCREMENT BY 1 NOCACHE;

-- Constrangeri de integritate (Cerinta Back-End 5)

-- CHECK pe tabelul de fapte: reguli de business pentru masuri
ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_CANT
  CHECK (CANTITATE > 0);
ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_SUBTOT
  CHECK (SUBTOTAL_FARA_TVA >= 0);
ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_TVA
  CHECK (SUMA_TVA >= 0);
ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_TOTAL
  CHECK (TOTAL_CU_TVA >= 0);
ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT CK_FAPT_DISC
  CHECK (DISCOUNT_PROC BETWEEN 0 AND 100);

-- CHECK pe DIM_TIMP: validam ca datele calendaristice au sens
ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_LUNA
  CHECK (LUNA BETWEEN 1 AND 12);
ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_ZI
  CHECK (ZI   BETWEEN 1 AND 31);
ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_WEEK
  CHECK (WEEKEND IN (0,1));
ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_TRIM
  CHECK (TRIMESTRU BETWEEN 1 AND 4);
ALTER TABLE DIM_TIMP ADD CONSTRAINT CK_TIMP_SEM
  CHECK (SEMESTRU  IN (1, 2));

-- ETL: populare dimensiuni din OLTP (Cerinta Back-End 4)

-- DIM_TIMP: calendarul 2023-2026 (1096 zile)
BEGIN
  FOR d IN 0..1095 LOOP
    DECLARE
      v_data DATE := TO_DATE('2023-01-01','YYYY-MM-DD') + d;
      v_dow  NUMBER := TO_NUMBER(TO_CHAR(v_data,'D'));  -- ziua saptamanii (1=dum, 7=sam)
    BEGIN
      INSERT INTO DIM_TIMP VALUES (
        v_data,
        TO_NUMBER(TO_CHAR(v_data,'YYYY')),
        CASE WHEN TO_NUMBER(TO_CHAR(v_data,'MM')) <= 6 THEN 1 ELSE 2 END,
        TO_NUMBER(TO_CHAR(v_data,'Q')),
        TO_NUMBER(TO_CHAR(v_data,'MM')),
        TO_CHAR(v_data,'Month','NLS_DATE_LANGUAGE=ROMANIAN'),
        TO_NUMBER(TO_CHAR(v_data,'IW')),
        TO_NUMBER(TO_CHAR(v_data,'DD')),
        v_dow,
        TO_CHAR(v_data,'Day','NLS_DATE_LANGUAGE=ROMANIAN'),
        CASE WHEN v_dow IN (1,7) THEN 1 ELSE 0 END
      );
    END;
  END LOOP;
  COMMIT;
END;
/

-- DIM_PACIENTI: copiem pacientii din OLTP
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
  SYSDATE  -- DATA_START = acum (SCD Tip 2: inregistrarea este curenta)
FROM stoma_oltp.PACIENTI p;

COMMIT;

-- DIM_MEDICI: copiem medicii din OLTP
INSERT INTO DIM_MEDICI (ID_MEDIC_DW, ID_MEDIC_OLTP, NUME, PRENUME, SPECIALIZARE, ACTIV)
SELECT
  seq_dw_medici.NEXTVAL,
  m.ID_MEDIC,
  m.NUME,
  m.PRENUME,
  m.SPECIALIZARE,
  m.ACTIV
FROM stoma_oltp.MEDICI m;

COMMIT;

-- DIM_SERVICII: copiem serviciile + derivam subcategoria
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
FROM stoma_oltp.SERVICII s;

COMMIT;

-- DIM_CABINETE: copiem cabinetele + derivam tipul din denumire
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
FROM stoma_oltp.CABINETE c;

COMMIT;

-- DIM_LOCATIE: extragem locatiile unice din tabelul pacienti
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
);

COMMIT;

-- DIM_METODA_PLATA: populata manual (dimensiune statica)
INSERT INTO DIM_METODA_PLATA VALUES (1, 'Cash',      'Numerar');
INSERT INTO DIM_METODA_PLATA VALUES (2, 'Card',       'Electronic');
INSERT INTO DIM_METODA_PLATA VALUES (3, 'Transfer',   'Electronic');
INSERT INTO DIM_METODA_PLATA VALUES (4, 'Asigurare',  'Tert platitor');
INSERT INTO DIM_METODA_PLATA VALUES (0, 'Necunoscut', 'N/A');

COMMIT;

-- FAPTE_SERVICII: incarcam datele de la OLTP
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
     WHERE DENUMIRE = f.METODA_PLATA), 0),    -- 0 = Necunoscut daca nu gasim match
  pr.ID_PROGRAMARE,                           -- cheie degenerata: referinta OLTP
  f.ID_FACTURA,                               -- cheie degenerata: referinta factura
  ps.CANTITATE,
  ps.PRET_APLICAT,
  ps.DISCOUNT_PROC,
  -- Calculam subtotalul si TVA-ul direct in ETL (19% TVA Romania)
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
WHERE pr.STATUS = 'Finalizata';

COMMIT;

-- FK-uri DEFERRABLE, adaugate dupa populare (Cerinta Back-End 5)

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_TIMP
  FOREIGN KEY (TIMP_ID) REFERENCES DIM_TIMP(ID_TIMP)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_PACIENT
  FOREIGN KEY (PACIENT_ID) REFERENCES DIM_PACIENTI(ID_PACIENT_DW)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_MEDIC
  FOREIGN KEY (MEDIC_ID) REFERENCES DIM_MEDICI(ID_MEDIC_DW)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_SERVICIU
  FOREIGN KEY (SERVICIU_ID) REFERENCES DIM_SERVICII(ID_SERVICIU_DW)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_CABINET
  FOREIGN KEY (CABINET_ID) REFERENCES DIM_CABINETE(ID_CABINET_DW)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE FAPTE_SERVICII ADD CONSTRAINT FK_FAPT_LOCATIE
  FOREIGN KEY (LOCATIE_ID) REFERENCES DIM_LOCATIE(ID_LOCATIE)
  DEFERRABLE INITIALLY DEFERRED;

-- Indecsi Bitmap si B-Tree LOCAL (Cerinta Back-End 6)

-- Bitmap pe FK-uri (cardinalitate mica = valori repetate = ideal pentru bitmap)
CREATE BITMAP INDEX idx_fapt_medic_bm    ON FAPTE_SERVICII(MEDIC_ID)
  LOCAL;  -- LOCAL = index per partitie (aliniat cu partitionarea RANGE)

CREATE BITMAP INDEX idx_fapt_serviciu_bm ON FAPTE_SERVICII(SERVICIU_ID)
  LOCAL;

CREATE BITMAP INDEX idx_fapt_cabinet_bm  ON FAPTE_SERVICII(CABINET_ID)
  LOCAL;

CREATE BITMAP INDEX idx_fapt_locatie_bm  ON FAPTE_SERVICII(LOCATIE_ID)
  LOCAL;

CREATE BITMAP INDEX idx_fapt_metoda_bm   ON FAPTE_SERVICII(METODA_PLATA_ID)
  LOCAL;

-- B-Tree pe coloane de filtrare frecventa (data si pacient au cardinalitate mare)
CREATE INDEX idx_fapt_timp      ON FAPTE_SERVICII(TIMP_ID)
  LOCAL;

CREATE INDEX idx_fapt_pacient   ON FAPTE_SERVICII(PACIENT_ID)
  LOCAL;

-- Index compus pe dimensiunea timp: accelereaza filtrarile pe AN+LUNA
CREATE INDEX idx_dim_timp_an_luna ON DIM_TIMP(AN, LUNA, ID_TIMP);

-- Index pe specializare medic (folosit in raportul de performanta medici)
CREATE INDEX idx_dim_medic_spec ON DIM_MEDICI(SPECIALIZARE);

-- Index pe categoria serviciului (folosit in raportul pe categorii)
CREATE INDEX idx_dim_serv_cat   ON DIM_SERVICII(CATEGORIE);

-- Obiecte DIMENSION cu ierarhii (Cerinta Back-End 7)

-- DIMENSION temporala: zi -> luna -> trimestru -> an
CREATE DIMENSION dim_timp_hier
  LEVEL zi        IS DIM_TIMP.ID_TIMP
  LEVEL luna      IS DIM_TIMP.LUNA
  LEVEL trimestru IS DIM_TIMP.TRIMESTRU
  LEVEL an        IS DIM_TIMP.AN

  HIERARCHY timp_roll_up (
    zi CHILD OF luna
    CHILD OF trimestru
    CHILD OF an
  )

  ATTRIBUTE zi        DETERMINES (DIM_TIMP.ZI_NUME, DIM_TIMP.ZI_SAPTAMANA,
                                   DIM_TIMP.WEEKEND, DIM_TIMP.SAPTAMANA_AN)
  ATTRIBUTE luna      DETERMINES DIM_TIMP.LUNA_NUME
  ATTRIBUTE trimestru DETERMINES DIM_TIMP.SEMESTRU;

-- DIMENSION servicii: serviciu -> subcategorie -> categorie
CREATE DIMENSION dim_servicii_hier
  LEVEL serviciu    IS DIM_SERVICII.ID_SERVICIU_DW
  LEVEL subcategorie IS DIM_SERVICII.SUBCATEGORIE
  LEVEL categorie   IS DIM_SERVICII.CATEGORIE

  HIERARCHY serv_roll_up (
    serviciu    CHILD OF subcategorie
    CHILD OF categorie
  )

  ATTRIBUTE serviciu    DETERMINES (DIM_SERVICII.DENUMIRE, DIM_SERVICII.PRET_LISTA,
                                     DIM_SERVICII.DURATA_MIN)
  ATTRIBUTE categorie   DETERMINES DIM_SERVICII.CATEGORIE;

-- DIMENSION geografica: pacient -> oras -> judet
CREATE DIMENSION dim_pacienti_geo
  LEVEL pacient IS DIM_PACIENTI.ID_PACIENT_DW
  LEVEL oras    IS DIM_PACIENTI.ORAS
  LEVEL judet   IS DIM_PACIENTI.JUDET

  HIERARCHY geo_roll_up (
    pacient CHILD OF oras
    CHILD OF judet
  )

  ATTRIBUTE pacient DETERMINES (DIM_PACIENTI.NUME, DIM_PACIENTI.PRENUME,
                                  DIM_PACIENTI.GRUPA_VARSTA);

-- Materialized view cu query rewrite (Cerinta Back-End 9)

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
  JOIN DIM_TIMP     t ON t.ID_TIMP          = f.TIMP_ID
  JOIN DIM_SERVICII s ON s.ID_SERVICIU_DW   = f.SERVICIU_ID
  JOIN DIM_MEDICI   m ON m.ID_MEDIC_DW      = f.MEDIC_ID
  JOIN DIM_LOCATIE  l ON l.ID_LOCATIE       = f.LOCATIE_ID
GROUP BY
  t.AN, t.TRIMESTRU, t.LUNA, t.LUNA_NUME,
  s.CATEGORIE, m.SPECIALIZARE,
  m.NUME, m.PRENUME, l.ORAS, l.JUDET;

-- Cerere complexa de optimizat + plan de executie (Cerinta Back-End 9)

-- VARIANTA 1: Fara optimizare (query pe tabelele originale, fara hint)
EXPLAIN PLAN FOR
SELECT
  dm.NUME || ' ' || dm.PRENUME   AS MEDIC,
  dm.SPECIALIZARE,
  dt.TRIMESTRU,
  ds.CATEGORIE,
  COUNT(f.ID_FAPT)               AS NR_SERVICII,
  SUM(f.TOTAL_CU_TVA)            AS VENIT_TOTAL,
  ROUND(AVG(f.PRET_UNITAR), 2)   AS PRET_MEDIU,
  RANK() OVER (
    PARTITION BY dt.TRIMESTRU
    ORDER BY SUM(f.TOTAL_CU_TVA) DESC
  ) AS RANK_TRIM
FROM
  FAPTE_SERVICII   f
  JOIN DIM_TIMP     dt ON dt.ID_TIMP        = f.TIMP_ID
  JOIN DIM_MEDICI   dm ON dm.ID_MEDIC_DW    = f.MEDIC_ID
  JOIN DIM_SERVICII ds ON ds.ID_SERVICIU_DW = f.SERVICIU_ID
WHERE dt.AN = 2024
GROUP BY
  dm.NUME, dm.PRENUME, dm.SPECIALIZARE, dt.TRIMESTRU, ds.CATEGORIE
ORDER BY dt.TRIMESTRU, VENIT_TOTAL DESC;

-- Plan varianta neoptimizata
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);

-- VARIANTA 2: Cu optimizare (redirectat catre MV + hint pe index)
EXPLAIN PLAN FOR
SELECT /*+ REWRITE(MV_VANZARI_LUNARE) INDEX(f idx_fapt_timp) */
  MEDIC_NUME || ' ' || MEDIC_PRENUME  AS MEDIC,
  SPECIALIZARE,
  TRIMESTRU,
  CATEGORIE,
  NR_SERVICII,
  TOTAL_CU_TVA                        AS VENIT_TOTAL,
  PRET_MEDIU_SERVICIU                 AS PRET_MEDIU,
  RANK() OVER (
    PARTITION BY TRIMESTRU
    ORDER BY TOTAL_CU_TVA DESC
  ) AS RANK_TRIM
FROM MV_VANZARI_LUNARE
WHERE AN = 2024
ORDER BY TRIMESTRU, VENIT_TOTAL DESC;

-- Plan varianta optimizata
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);

-- Rapoarte SQL analitice (Cerinta Back-End 10)

-- Raport 1: venituri pe luna si categorie (ROLLUP, GROUPING)
SELECT
  dt.AN,
  dt.LUNA_NUME,
  ds.CATEGORIE,
  GROUPING(dt.LUNA_NUME)  AS IS_SUBTOTAL_LUNA,  -- 1 = rand subtotal pe luna
  GROUPING(ds.CATEGORIE)  AS IS_SUBTOTAL_CAT,   -- 1 = rand subtotal pe categorie
  COUNT(f.ID_FAPT)        AS NR_SERVICII,
  SUM(f.TOTAL_CU_TVA)     AS VENIT_TOTAL,
  SUM(f.SUMA_PLATITA)     AS INCASAT_TOTAL
FROM
  FAPTE_SERVICII   f
  JOIN DIM_TIMP     dt ON dt.ID_TIMP        = f.TIMP_ID
  JOIN DIM_SERVICII ds ON ds.ID_SERVICIU_DW = f.SERVICIU_ID
WHERE dt.AN IN (2024, 2025)
-- ROLLUP(AN, LUNA, CATEGORIE) genereaza: total/an/luna/categorie + subtotaluri
GROUP BY ROLLUP (dt.AN, dt.LUNA_NUME, ds.CATEGORIE)
ORDER BY dt.AN, dt.LUNA, ds.CATEGORIE;

-- Raport 2: performanta medici (RANK, PERCENT_RANK)
SELECT
  dm.NUME || ' ' || dm.PRENUME  AS MEDIC,
  dm.SPECIALIZARE,
  COUNT(DISTINCT f.ID_PROGRAMARE_OLTP)  AS NR_PROGRAMARI,
  COUNT(f.ID_FAPT)                      AS NR_SERVICII_EFECTUATE,
  SUM(f.TOTAL_CU_TVA)                   AS VENIT_TOTAL,
  ROUND(AVG(f.PRET_UNITAR), 2)          AS PRET_MEDIU_SERVICIU,
  RANK() OVER (ORDER BY SUM(f.TOTAL_CU_TVA) DESC)       AS RANK_VENIT,
  ROUND(PERCENT_RANK() OVER (ORDER BY SUM(f.TOTAL_CU_TVA) DESC) * 100, 1)
                                         AS PERCENTIL_VENIT
FROM
  FAPTE_SERVICII  f
  JOIN DIM_MEDICI dm ON dm.ID_MEDIC_DW = f.MEDIC_ID
  JOIN DIM_TIMP   dt ON dt.ID_TIMP     = f.TIMP_ID
WHERE dt.AN = 2024
GROUP BY dm.ID_MEDIC_DW, dm.NUME, dm.PRENUME, dm.SPECIALIZARE
ORDER BY VENIT_TOTAL DESC;

-- Raport 3: evolutia lunara, total cumulat si variatie (SUM OVER, LAG)
SELECT
  dt.AN,
  dt.TRIMESTRU,
  dt.LUNA,
  dt.LUNA_NUME,
  COUNT(f.ID_FAPT)                       AS NR_SERVICII,
  SUM(f.TOTAL_CU_TVA)                    AS VENIT_LUNA,
  SUM(SUM(f.TOTAL_CU_TVA)) OVER (
    PARTITION BY dt.AN, dt.TRIMESTRU
    ORDER BY dt.LUNA
    ROWS UNBOUNDED PRECEDING
  )                                       AS VENIT_CUMULAT_TRIM,
  LAG(SUM(f.TOTAL_CU_TVA), 1) OVER (
    PARTITION BY dt.AN ORDER BY dt.LUNA
  )                                       AS VENIT_LUNA_PREC,
  -- NULLIF previne impartirea la zero daca luna precedenta are venit 0
  ROUND(
    (SUM(f.TOTAL_CU_TVA) - LAG(SUM(f.TOTAL_CU_TVA),1) OVER (
      PARTITION BY dt.AN ORDER BY dt.LUNA)) /
    NULLIF(LAG(SUM(f.TOTAL_CU_TVA),1) OVER (
      PARTITION BY dt.AN ORDER BY dt.LUNA), 0) * 100, 2
  )                                       AS PCT_VARIATIE
FROM
  FAPTE_SERVICII  f
  JOIN DIM_TIMP   dt ON dt.ID_TIMP = f.TIMP_ID
WHERE dt.AN = 2024
GROUP BY dt.AN, dt.TRIMESTRU, dt.LUNA, dt.LUNA_NUME
ORDER BY dt.AN, dt.LUNA;

-- Raport 4: segmentare pacienti pe cheltuieli (NTILE)
SELECT
  dp.NUME || ' ' || dp.PRENUME  AS PACIENT,
  dp.ORAS,
  dp.JUDET,
  dp.GRUPA_VARSTA,
  COUNT(DISTINCT f.ID_PROGRAMARE_OLTP)  AS NR_VIZITE,
  COUNT(f.ID_FAPT)                      AS NR_SERVICII,
  SUM(f.TOTAL_CU_TVA)                   AS CHELTUIELI_TOTALE,
  ROUND(AVG(f.TOTAL_CU_TVA), 2)         AS CHELTUIALA_MEDIE_SERVICIU,
  NTILE(4) OVER (ORDER BY SUM(f.TOTAL_CU_TVA) DESC)  AS QUARTIL_CHELTUIELI,
  CASE NTILE(4) OVER (ORDER BY SUM(f.TOTAL_CU_TVA) DESC)
    WHEN 1 THEN 'VIP'       -- top 25% cheltuitori
    WHEN 2 THEN 'Premium'   -- 25-50%
    WHEN 3 THEN 'Standard'  -- 50-75%
    ELSE       'Basic'      -- ultimii 25%
  END                                   AS SEGMENT_PACIENT
FROM
  FAPTE_SERVICII   f
  JOIN DIM_PACIENTI dp ON dp.ID_PACIENT_DW = f.PACIENT_ID
GROUP BY
  dp.ID_PACIENT_DW, dp.NUME, dp.PRENUME,
  dp.ORAS, dp.JUDET, dp.GRUPA_VARSTA
ORDER BY CHELTUIELI_TOTALE DESC;

-- Raport 5: utilizare si venituri cabinete (CUBE)
SELECT
  dc.DENUMIRE                           AS CABINET,
  dc.TIP_CABINET,
  COALESCE(TO_CHAR(dt.AN), 'TOTAL')     AS AN,  -- TOTAL = randul de subtotal
  COUNT(DISTINCT f.ID_PROGRAMARE_OLTP)  AS NR_PROGRAMARI,
  COUNT(f.ID_FAPT)                      AS NR_SERVICII,
  SUM(f.TOTAL_CU_TVA)                   AS VENIT_TOTAL,
  ROUND(SUM(f.TOTAL_CU_TVA) /
    NULLIF(SUM(SUM(f.TOTAL_CU_TVA)) OVER (), 0) * 100, 2)
                                         AS PCT_DIN_TOTAL
FROM
  FAPTE_SERVICII   f
  JOIN DIM_CABINETE dc ON dc.ID_CABINET_DW = f.CABINET_ID
  JOIN DIM_TIMP     dt ON dt.ID_TIMP       = f.TIMP_ID
-- CUBE(CABINET, TIP_CABINET, AN) = toate combinatiile de subtotaluri
GROUP BY CUBE(dc.DENUMIRE, dc.TIP_CABINET, dt.AN)
-- Filtram: vrem fie un cabinet specific, fie total general (nu combinatii intermediare)
HAVING GROUPING(dc.DENUMIRE) = 0 OR GROUPING(dc.DENUMIRE) = 1
ORDER BY dc.DENUMIRE NULLS LAST, dt.AN NULLS LAST;

-- Raport 6: top 3 servicii per categorie (DENSE_RANK)
SELECT *
FROM (
  SELECT
    ds.CATEGORIE,
    ds.DENUMIRE,
    COUNT(f.ID_FAPT)       AS NR_EFECTUAT,
    SUM(f.TOTAL_CU_TVA)    AS VENIT_TOTAL,
    DENSE_RANK() OVER (
      PARTITION BY ds.CATEGORIE
      ORDER BY SUM(f.TOTAL_CU_TVA) DESC
    ) AS RANK_IN_CAT
  FROM
    FAPTE_SERVICII   f
    JOIN DIM_SERVICII ds ON ds.ID_SERVICIU_DW = f.SERVICIU_ID
  GROUP BY ds.CATEGORIE, ds.DENUMIRE
)
WHERE RANK_IN_CAT <= 3
ORDER BY CATEGORIE, RANK_IN_CAT;

-- Verificare finala
SELECT 'DIM_TIMP'         AS tabel, COUNT(*) AS nr FROM DIM_TIMP UNION ALL
SELECT 'DIM_PACIENTI'     AS tabel, COUNT(*) AS nr FROM DIM_PACIENTI UNION ALL
SELECT 'DIM_MEDICI'       AS tabel, COUNT(*) AS nr FROM DIM_MEDICI UNION ALL
SELECT 'DIM_SERVICII'     AS tabel, COUNT(*) AS nr FROM DIM_SERVICII UNION ALL
SELECT 'DIM_CABINETE'     AS tabel, COUNT(*) AS nr FROM DIM_CABINETE UNION ALL
SELECT 'DIM_LOCATIE'      AS tabel, COUNT(*) AS nr FROM DIM_LOCATIE UNION ALL
SELECT 'DIM_METODA_PLATA' AS tabel, COUNT(*) AS nr FROM DIM_METODA_PLATA UNION ALL
SELECT 'FAPTE_SERVICII'   AS tabel, COUNT(*) AS nr FROM FAPTE_SERVICII;
