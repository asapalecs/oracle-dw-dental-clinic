#!/usr/bin/env python3
"""Goleste schema OLTP si reinsereaza datele cu ID-uri explicite (doar pentru dezvoltare)."""
import os
import sys

import oracledb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import connect_oltp as conn_oltp  # noqa: E402

print("=== Curatare + reinserare cu ID-uri explicite ===\n")

c = conn_oltp()
cur = c.cursor()
print("ID-uri actuale:")
for t,col in [("CABINETE","ID_CABINET"),("MEDICI","ID_MEDIC"),
              ("PACIENTI","ID_PACIENT"),("SERVICII","ID_SERVICIU")]:
    cur.execute(f"SELECT MIN({col}), MAX({col}), COUNT(*) FROM {t}")
    mn, mx, cnt = cur.fetchone()
    print(f"  {t}: min={mn}, max={mx}, count={cnt}")
c.close()

print("\nTrunchez toate tabelele...")

c = conn_oltp()
cur = c.cursor()

# Dezactivare temporara FK
fks = [
    ("ASISTENTE", "FK_ASIST_CABINET"),
    ("PROGRAMARI", "FK_PROG_PACIENT"),
    ("PROGRAMARI", "FK_PROG_MEDIC"),
    ("PROGRAMARI", "FK_PROG_CABINET"),
    ("PROGRAMARI_SERVICII", "FK_PS_PROGRAMARE"),
    ("PROGRAMARI_SERVICII", "FK_PS_SERVICIU"),
    ("FACTURI", "FK_FACT_PROG"),
    ("FACTURI", "FK_FACT_PACIENT"),
    ("UTILIZARI_MATERIALE", "FK_UTIL_PROGRAMARE"),
    ("UTILIZARI_MATERIALE", "FK_UTIL_MATERIAL"),
    ("ISTORIC_MEDICAL", "FK_IST_PACIENT"),
    ("ISTORIC_MEDICAL", "FK_IST_MEDIC"),
    ("ISTORIC_MEDICAL", "FK_IST_PROGRAMARE"),
]
for tbl, fk in fks:
    try:
        cur.execute(f"ALTER TABLE {tbl} DISABLE CONSTRAINT {fk}")
    except: pass

for t in ["UTILIZARI_MATERIALE","FACTURI","PROGRAMARI_SERVICII",
          "PROGRAMARI","ISTORIC_MEDICAL","PACIENTI","ASISTENTE",
          "MEDICI","MATERIALE","SERVICII","CABINETE"]:
    try:
        cur.execute(f"TRUNCATE TABLE {t}")
        print(f"  TRUNCATE {t} OK")
    except Exception as e:
        print(f"  TRUNCATE {t} EROARE: {e}")

for tbl, fk in fks:
    try:
        cur.execute(f"ALTER TABLE {tbl} ENABLE CONSTRAINT {fk}")
    except: pass

c.commit()
c.close()

print("\nResetez secventele...")
c = conn_oltp()
cur = c.cursor()
seqs = ["SEQ_PACIENTI","SEQ_MEDICI","SEQ_ASISTENTE","SEQ_CABINETE",
        "SEQ_SERVICII","SEQ_PROGRAMARI","SEQ_PROG_SERVICII",
        "SEQ_FACTURI","SEQ_MATERIALE","SEQ_UTILIZARI_MAT","SEQ_ISTORIC"]
for s in seqs:
    try:
        cur.execute(f"ALTER SEQUENCE {s} RESTART START WITH 1")
        print(f"  {s} resetat")
    except Exception as e:
        print(f"  {s} EROARE: {e}")
c.commit()
c.close()

print("\nReinserare cu ID-uri explicite...")

def run(conn_fn, sqls, label):
    c = conn_fn()
    cur = c.cursor()
    ok = err = 0
    for sql in sqls:
        sql = sql.strip()
        if not sql: continue
        try:
            cur.execute(sql)
            ok += 1
        except Exception as e:
            print(f"  EROARE [{label}] {str(e)[:80]}: {sql[:60]}")
            err += 1
    c.commit()
    c.close()
    return ok, err

cabinete = [
    "INSERT INTO CABINETE VALUES (1,'Cabinet 1 - Consultatie',0,1,'Unit dentar Castellini, Radiograf periapical','Y')",
    "INSERT INTO CABINETE VALUES (2,'Cabinet 2 - Chirurgie',1,1,'Unit dentar Sirona, Lampa scialitic, Aspirator chirurgical','Y')",
    "INSERT INTO CABINETE VALUES (3,'Cabinet 3 - Ortodontie',1,1,'Unit dentar KaVo, Scanner intraoral iTero','Y')",
    "INSERT INTO CABINETE VALUES (4,'Cabinet 4 - Radiologie',0,2,'CBCT Planmeca, OPG Orthophos','Y')",
    "INSERT INTO CABINETE VALUES (5,'Cabinet 5 - Estetica',2,1,'Unit dentar A-dec, Lampa fotopolimerizare LED','Y')",
]
medici = [
    "INSERT INTO MEDICI VALUES (1,'Ionescu','Andrei','Medicina dentara generala','0722111001','a.ionescu@stomaclinic.ro',TO_DATE('2015-03-01','YYYY-MM-DD'),12000,'Y')",
    "INSERT INTO MEDICI VALUES (2,'Popescu','Maria','Ortodontie','0722111002','m.popescu@stomaclinic.ro',TO_DATE('2017-06-15','YYYY-MM-DD'),14000,'Y')",
    "INSERT INTO MEDICI VALUES (3,'Gheorghe','Constantin','Chirurgie oro-maxilo-faciala','0722111003','c.gheorghe@stomaclinic.ro',TO_DATE('2012-01-10','YYYY-MM-DD'),16000,'Y')",
    "INSERT INTO MEDICI VALUES (4,'Munteanu','Elena','Endodontie','0722111004','e.munteanu@stomaclinic.ro',TO_DATE('2019-09-01','YYYY-MM-DD'),13000,'Y')",
    "INSERT INTO MEDICI VALUES (5,'Dumitrescu','Bogdan','Estetica dentara','0722111005','b.dumitrescu@stomaclinic.ro',TO_DATE('2020-02-01','YYYY-MM-DD'),11000,'Y')",
]
asistente = [
    "INSERT INTO ASISTENTE VALUES (1,'Radu','Cristina','0733200001','c.radu@stomaclinic.ro',TO_DATE('2016-04-01','YYYY-MM-DD'),1,'Y')",
    "INSERT INTO ASISTENTE VALUES (2,'Stan','Ioana','0733200002','i.stan@stomaclinic.ro',TO_DATE('2018-07-01','YYYY-MM-DD'),2,'Y')",
    "INSERT INTO ASISTENTE VALUES (3,'Florea','Alina','0733200003','a.florea@stomaclinic.ro',TO_DATE('2021-01-10','YYYY-MM-DD'),3,'Y')",
]
pacienti = [
    "INSERT INTO PACIENTI VALUES (1,'Mihai','Ion','1850312345678',TO_DATE('1985-03-12','YYYY-MM-DD'),'0744300001','ion.mihai@gmail.com','Str. Florilor 10','Bucuresti','Ilfov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (2,'Niculescu','Ana','2900614234567',TO_DATE('1990-06-14','YYYY-MM-DD'),'0744300002','ana.niculescu@gmail.com','Bd. Unirii 25','Bucuresti','Ilfov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (3,'Barbu','Radu','1780422123456',TO_DATE('1978-04-22','YYYY-MM-DD'),'0744300003','radu.barbu@yahoo.com','Str. Primaverii 5','Cluj-Napoca','Cluj',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (4,'Constantin','Mihaela','2950810345678',TO_DATE('1995-08-10','YYYY-MM-DD'),'0744300004','m.constantin@gmail.com','Calea Victoriei 100','Bucuresti','Ilfov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (5,'Lazar','Gheorghe','1680115234567',TO_DATE('1968-01-15','YYYY-MM-DD'),'0744300005','gh.lazar@yahoo.com','Str. Republicii 7','Brasov','Brasov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (6,'Popa','Daniela','2820920345678',TO_DATE('1982-09-20','YYYY-MM-DD'),'0744300006','d.popa@gmail.com','Sos. Nordului 33','Bucuresti','Ilfov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (7,'Toma','Alexandru','1000203456789',TO_DATE('2000-02-03','YYYY-MM-DD'),'0744300007','alex.toma@gmail.com','Bd. Magheru 18','Bucuresti','Ilfov',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (8,'Dima','Roxana','2930707234567',TO_DATE('1993-07-07','YYYY-MM-DD'),'0744300008','rox.dima@yahoo.com','Str. Eminescu 3','Iasi','Iasi',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (9,'Voicu','Marius','1751122345670',TO_DATE('1975-11-22','YYYY-MM-DD'),'0744300009','m.voicu@gmail.com','Str. Stefan cel Mare','Timisoara','Timis',SYSDATE,'Y')",
    "INSERT INTO PACIENTI VALUES (10,'Neagu','Laura','2880401234568',TO_DATE('1988-04-01','YYYY-MM-DD'),'0744300010','l.neagu@gmail.com','Aleea Florilor 4','Bucuresti','Ilfov',SYSDATE,'Y')",
]
servicii = [
    "INSERT INTO SERVICII VALUES (1,'Consultatie initiala','Examinare clinica completa si plan de tratament','Preventie',150,30,19,'Y')",
    "INSERT INTO SERVICII VALUES (2,'Detartraj ultrasonic','Curatare depozite de tartru prin ultrasunete','Preventie',200,45,19,'Y')",
    "INSERT INTO SERVICII VALUES (3,'Periaj profesional + fluorizare','Periaj cu pasta profilactica si aplicare gel fluorurat','Preventie',180,30,19,'Y')",
    "INSERT INTO SERVICII VALUES (4,'Plomba compozit (1 fata)','Obturatie din compozit pentru carie mica','Restauratoare',350,60,19,'Y')",
    "INSERT INTO SERVICII VALUES (5,'Plomba compozit (2-3 fete)','Obturatie compozit pentru carie medie/mare','Restauratoare',500,75,19,'Y')",
    "INSERT INTO SERVICII VALUES (6,'Tratament canal (monoradicular)','Tratament endodontic dinte cu un canal radicular','Endodontie',800,90,19,'Y')",
    "INSERT INTO SERVICII VALUES (7,'Tratament canal (multiradicular)','Tratament endodontic dinte cu mai multe canale','Endodontie',1200,120,19,'Y')",
    "INSERT INTO SERVICII VALUES (8,'Extractie simpla','Extractia unui dinte fara complicatii','Chirurgie',300,30,19,'Y')",
    "INSERT INTO SERVICII VALUES (9,'Extractie chirurgicala','Extractie dinte inclus sau partial erupt','Chirurgie',600,60,19,'Y')",
    "INSERT INTO SERVICII VALUES (10,'Aparat ortodontic metalic','Montare aparat fix metalic (per arcada)','Ortodontie',2500,120,19,'Y')",
    "INSERT INTO SERVICII VALUES (11,'Aparat ortodontic ceramic','Montare aparat fix ceramic (per arcada)','Ortodontie',3500,120,19,'Y')",
    "INSERT INTO SERVICII VALUES (12,'Consultatie ortodontica','Evaluare si plan de tratament ortodontic','Ortodontie',200,45,19,'Y')",
    "INSERT INTO SERVICII VALUES (13,'Albire dentara profesionala','Sistem Zoom whitening in cabinet','Estetica',1200,90,19,'Y')",
    "INSERT INTO SERVICII VALUES (14,'Fatete ceramice (per dinte)','Fatete din ceramica pentru estetic superioara','Estetica',2000,90,19,'Y')",
    "INSERT INTO SERVICII VALUES (15,'Radiografie retroalveolara','Radiografie periapicala digitala','Radiologie',80,10,19,'Y')",
    "INSERT INTO SERVICII VALUES (16,'OPG (panoramica)','Ortopantomograma digitala','Radiologie',180,15,19,'Y')",
    "INSERT INTO SERVICII VALUES (17,'Coroana ceramica (zirconia)','Coroana dentara din zirconia','Protetica',2500,120,19,'Y')",
    "INSERT INTO SERVICII VALUES (18,'Detartraj + periaj (mentinere)','Sedinta de igienizare profesionala periodica','Preventie',300,60,19,'Y')",
]
materiale = [
    "INSERT INTO MATERIALE VALUES (1,'Compozit fotopolimerizabil Filtek Z350','g',500,85,'Restauratoare','3M ESPE','Y')",
    "INSERT INTO MATERIALE VALUES (2,'Sistem adeziv Scotchbond','ml',100,120,'Restauratoare','3M ESPE','Y')",
    "INSERT INTO MATERIALE VALUES (3,'Hipoclorit de sodiu 5.25%','ml',2000,0.05,'Endodontie','Clinic','Y')",
    "INSERT INTO MATERIALE VALUES (4,'Ace endodontice Protaper Next','set',50,180,'Endodontie','Dentsply','Y')",
    "INSERT INTO MATERIALE VALUES (5,'Material amprenta polivinil siloxan','g',300,55,'Protetica','Zhermack','Y')",
    "INSERT INTO MATERIALE VALUES (6,'Anestezic Ubistezin 4%','fiola',200,8,'Chirurgie','3M ESPE','Y')",
    "INSERT INTO MATERIALE VALUES (7,'Gel fluor Elmex','ml',500,0.30,'Preventie','GABA','Y')",
    "INSERT INTO MATERIALE VALUES (8,'Vata chirurgicala','g',1000,0.05,'Chirurgie','Hartmann','Y')",
    "INSERT INTO MATERIALE VALUES (9,'Fir sutura 3-0','buc',100,12,'Chirurgie','Ethicon','Y')",
    "INSERT INTO MATERIALE VALUES (10,'Pasta profilactica','g',400,0.20,'Preventie','Oral-B','Y')",
]
programari = [
    "INSERT INTO PROGRAMARI VALUES (1,1,1,1,TO_DATE('2024-01-10','YYYY-MM-DD'),'10:00','10:30','Finalizata','Prima vizita',SYSDATE-480)",
    "INSERT INTO PROGRAMARI VALUES (2,2,2,3,TO_DATE('2024-01-15','YYYY-MM-DD'),'11:00','12:00','Finalizata','Consultatie ortodontie',SYSDATE-475)",
    "INSERT INTO PROGRAMARI VALUES (3,3,3,2,TO_DATE('2024-02-05','YYYY-MM-DD'),'09:00','09:30','Finalizata',NULL,SYSDATE-455)",
    "INSERT INTO PROGRAMARI VALUES (4,4,5,5,TO_DATE('2024-02-20','YYYY-MM-DD'),'14:00','15:00','Finalizata','Albire + consultatie',SYSDATE-440)",
    "INSERT INTO PROGRAMARI VALUES (5,1,1,1,TO_DATE('2024-03-03','YYYY-MM-DD'),'09:30','10:30','Finalizata',NULL,SYSDATE-430)",
    "INSERT INTO PROGRAMARI VALUES (6,5,4,4,TO_DATE('2024-03-12','YYYY-MM-DD'),'10:00','10:15','Finalizata','OPG cerut de medic',SYSDATE-421)",
    "INSERT INTO PROGRAMARI VALUES (7,2,2,3,TO_DATE('2024-04-08','YYYY-MM-DD'),'11:00','12:00','Finalizata','Control aparat ortodontic',SYSDATE-395)",
    "INSERT INTO PROGRAMARI VALUES (8,6,1,1,TO_DATE('2024-04-15','YYYY-MM-DD'),'15:00','16:00','Finalizata',NULL,SYSDATE-388)",
    "INSERT INTO PROGRAMARI VALUES (9,3,3,2,TO_DATE('2024-05-06','YYYY-MM-DD'),'09:00','10:00','Finalizata','Extractie molar 3',SYSDATE-367)",
    "INSERT INTO PROGRAMARI VALUES (10,7,5,5,TO_DATE('2024-05-20','YYYY-MM-DD'),'10:00','11:30','Finalizata','Albire dentara',SYSDATE-353)",
    "INSERT INTO PROGRAMARI VALUES (11,8,1,1,TO_DATE('2024-06-03','YYYY-MM-DD'),'12:00','12:30','Finalizata',NULL,SYSDATE-339)",
    "INSERT INTO PROGRAMARI VALUES (12,9,4,4,TO_DATE('2024-06-17','YYYY-MM-DD'),'09:00','09:15','Finalizata','Radiografie urgenta',SYSDATE-325)",
    "INSERT INTO PROGRAMARI VALUES (13,10,1,1,TO_DATE('2024-07-01','YYYY-MM-DD'),'10:00','11:00','Finalizata','Tratament canal',SYSDATE-311)",
    "INSERT INTO PROGRAMARI VALUES (14,1,1,1,TO_DATE('2024-07-22','YYYY-MM-DD'),'09:00','10:00','Finalizata','Detartraj periodic',SYSDATE-290)",
    "INSERT INTO PROGRAMARI VALUES (15,4,5,5,TO_DATE('2024-08-05','YYYY-MM-DD'),'11:00','12:30','Finalizata','Fatete ceramice evaluare',SYSDATE-276)",
    "INSERT INTO PROGRAMARI VALUES (16,5,3,2,TO_DATE('2024-08-19','YYYY-MM-DD'),'14:00','14:45','Finalizata',NULL,SYSDATE-262)",
    "INSERT INTO PROGRAMARI VALUES (17,6,4,4,TO_DATE('2024-09-09','YYYY-MM-DD'),'10:00','10:15','Finalizata',NULL,SYSDATE-241)",
    "INSERT INTO PROGRAMARI VALUES (18,7,5,5,TO_DATE('2024-09-23','YYYY-MM-DD'),'15:00','16:00','Finalizata',NULL,SYSDATE-227)",
    "INSERT INTO PROGRAMARI VALUES (19,8,1,1,TO_DATE('2024-10-07','YYYY-MM-DD'),'09:00','10:00','Finalizata',NULL,SYSDATE-213)",
    "INSERT INTO PROGRAMARI VALUES (20,9,3,3,TO_DATE('2024-10-21','YYYY-MM-DD'),'11:00','12:00','Finalizata',NULL,SYSDATE-199)",
    "INSERT INTO PROGRAMARI VALUES (21,10,2,2,TO_DATE('2024-11-04','YYYY-MM-DD'),'10:00','10:30','Finalizata',NULL,SYSDATE-185)",
    "INSERT INTO PROGRAMARI VALUES (22,1,1,1,TO_DATE('2024-11-18','YYYY-MM-DD'),'12:00','13:00','Finalizata','Coroana zirconia',SYSDATE-171)",
    "INSERT INTO PROGRAMARI VALUES (23,2,2,3,TO_DATE('2024-12-02','YYYY-MM-DD'),'09:00','10:00','Finalizata',NULL,SYSDATE-157)",
    "INSERT INTO PROGRAMARI VALUES (24,3,3,2,TO_DATE('2024-12-16','YYYY-MM-DD'),'10:00','11:00','Finalizata',NULL,SYSDATE-143)",
    "INSERT INTO PROGRAMARI VALUES (25,4,5,5,TO_DATE('2025-01-13','YYYY-MM-DD'),'14:00','16:00','Finalizata','Fatete ceramice 2 dinti',SYSDATE-132)",
    "INSERT INTO PROGRAMARI VALUES (26,5,1,1,TO_DATE('2025-01-27','YYYY-MM-DD'),'10:00','10:30','Finalizata',NULL,SYSDATE-118)",
    "INSERT INTO PROGRAMARI VALUES (27,6,3,2,TO_DATE('2025-02-10','YYYY-MM-DD'),'09:00','09:30','Finalizata',NULL,SYSDATE-103)",
    "INSERT INTO PROGRAMARI VALUES (28,7,5,5,TO_DATE('2025-02-24','YYYY-MM-DD'),'11:00','12:30','Finalizata',NULL,SYSDATE-89)",
    "INSERT INTO PROGRAMARI VALUES (29,8,1,1,TO_DATE('2025-03-10','YYYY-MM-DD'),'10:00','11:00','Finalizata',NULL,SYSDATE-75)",
    "INSERT INTO PROGRAMARI VALUES (30,9,3,3,TO_DATE('2025-03-24','YYYY-MM-DD'),'14:00','15:00','Finalizata',NULL,SYSDATE-61)",
    "INSERT INTO PROGRAMARI VALUES (31,10,4,4,TO_DATE('2025-04-07','YYYY-MM-DD'),'09:00','09:15','Finalizata',NULL,SYSDATE-47)",
    "INSERT INTO PROGRAMARI VALUES (32,1,1,1,TO_DATE('2025-04-21','YYYY-MM-DD'),'10:00','11:00','Finalizata',NULL,SYSDATE-33)",
    "INSERT INTO PROGRAMARI VALUES (33,2,2,3,TO_DATE('2025-05-05','YYYY-MM-DD'),'11:00','12:00','Finalizata',NULL,SYSDATE-19)",
    "INSERT INTO PROGRAMARI VALUES (34,3,3,2,TO_DATE('2025-05-19','YYYY-MM-DD'),'09:00','09:30','Programata',NULL,SYSDATE-5)",
    "INSERT INTO PROGRAMARI VALUES (35,4,1,1,TO_DATE('2025-05-26','YYYY-MM-DD'),'15:00','16:00','Programata',NULL,SYSDATE)",
]
ps = [
    "INSERT INTO PROGRAMARI_SERVICII VALUES (1,1,1,1,150,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (2,1,15,1,80,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (3,2,12,1,200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (4,3,8,1,300,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (5,4,13,1,1200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (6,4,1,1,150,10)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (7,5,2,1,200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (8,5,3,1,180,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (9,6,16,1,180,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (10,7,12,1,200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (11,8,4,1,350,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (12,8,15,1,80,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (13,9,9,1,600,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (14,10,13,1,1200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (15,11,1,1,150,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (16,12,15,1,80,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (17,13,6,1,800,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (18,13,15,1,80,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (19,14,18,1,300,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (20,15,14,1,2000,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (21,16,5,1,500,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (22,17,15,1,80,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (23,18,13,1,1200,5)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (24,19,4,2,350,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (25,20,10,1,2500,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (26,21,2,1,200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (27,22,17,1,2500,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (28,22,7,1,800,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (29,23,12,1,200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (30,24,8,1,300,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (31,25,14,2,2000,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (32,26,1,1,150,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (33,27,9,1,600,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (34,28,13,1,1200,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (35,29,6,1,800,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (36,30,11,1,3500,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (37,31,16,1,180,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (38,32,18,1,300,0)",
    "INSERT INTO PROGRAMARI_SERVICII VALUES (39,33,12,1,200,0)",
]
facturi = [
    "INSERT INTO FACTURI VALUES (1,1,1,TO_DATE('2024-01-10','YYYY-MM-DD'),230,43.70,273.70,273.70,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (2,2,2,TO_DATE('2024-01-15','YYYY-MM-DD'),200,38.00,238.00,238.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (3,3,3,TO_DATE('2024-02-05','YYYY-MM-DD'),300,57.00,357.00,357.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (4,4,4,TO_DATE('2024-02-20','YYYY-MM-DD'),1485,282.15,1767.15,1767.15,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (5,5,5,TO_DATE('2024-03-03','YYYY-MM-DD'),380,72.20,452.20,452.20,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (6,6,6,TO_DATE('2024-03-12','YYYY-MM-DD'),180,34.20,214.20,214.20,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (7,7,7,TO_DATE('2024-04-08','YYYY-MM-DD'),200,38.00,238.00,238.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (8,8,8,TO_DATE('2024-04-15','YYYY-MM-DD'),430,81.70,511.70,511.70,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (9,9,9,TO_DATE('2024-05-06','YYYY-MM-DD'),600,114.00,714.00,714.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (10,10,10,TO_DATE('2024-05-20','YYYY-MM-DD'),1200,228.00,1428.00,1428.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (11,11,8,TO_DATE('2024-06-03','YYYY-MM-DD'),150,28.50,178.50,178.50,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (12,12,9,TO_DATE('2024-06-17','YYYY-MM-DD'),80,15.20,95.20,95.20,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (13,13,10,TO_DATE('2024-07-01','YYYY-MM-DD'),880,167.20,1047.20,1000.00,'Transfer','Partiala')",
    "INSERT INTO FACTURI VALUES (14,14,1,TO_DATE('2024-07-22','YYYY-MM-DD'),300,57.00,357.00,357.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (15,15,4,TO_DATE('2024-08-05','YYYY-MM-DD'),2000,380.00,2380.00,2380.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (16,16,5,TO_DATE('2024-08-19','YYYY-MM-DD'),500,95.00,595.00,595.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (17,17,6,TO_DATE('2024-09-09','YYYY-MM-DD'),80,15.20,95.20,95.20,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (18,18,7,TO_DATE('2024-09-23','YYYY-MM-DD'),1140,216.60,1356.60,1356.60,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (19,19,8,TO_DATE('2024-10-07','YYYY-MM-DD'),700,133.00,833.00,833.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (20,20,9,TO_DATE('2024-10-21','YYYY-MM-DD'),2500,475.00,2975.00,2975.00,'Transfer','Achitata')",
    "INSERT INTO FACTURI VALUES (21,21,10,TO_DATE('2024-11-04','YYYY-MM-DD'),200,38.00,238.00,238.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (22,22,1,TO_DATE('2024-11-18','YYYY-MM-DD'),3300,627.00,3927.00,3927.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (23,23,2,TO_DATE('2024-12-02','YYYY-MM-DD'),200,38.00,238.00,238.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (24,24,3,TO_DATE('2024-12-16','YYYY-MM-DD'),300,57.00,357.00,0.00,'Asigurare','Neplatita')",
    "INSERT INTO FACTURI VALUES (25,25,4,TO_DATE('2025-01-13','YYYY-MM-DD'),4000,760.00,4760.00,4760.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (26,26,5,TO_DATE('2025-01-27','YYYY-MM-DD'),150,28.50,178.50,178.50,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (27,27,6,TO_DATE('2025-02-10','YYYY-MM-DD'),600,114.00,714.00,714.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (28,28,7,TO_DATE('2025-02-24','YYYY-MM-DD'),1200,228.00,1428.00,1428.00,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (29,29,8,TO_DATE('2025-03-10','YYYY-MM-DD'),800,152.00,952.00,952.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (30,30,9,TO_DATE('2025-03-24','YYYY-MM-DD'),3500,665.00,4165.00,4165.00,'Transfer','Achitata')",
    "INSERT INTO FACTURI VALUES (31,31,10,TO_DATE('2025-04-07','YYYY-MM-DD'),180,34.20,214.20,214.20,'Cash','Achitata')",
    "INSERT INTO FACTURI VALUES (32,32,1,TO_DATE('2025-04-21','YYYY-MM-DD'),300,57.00,357.00,357.00,'Card','Achitata')",
    "INSERT INTO FACTURI VALUES (33,33,2,TO_DATE('2025-05-05','YYYY-MM-DD'),200,38.00,238.00,238.00,'Cash','Achitata')",
]
utilizari = [
    "INSERT INTO UTILIZARI_MATERIALE VALUES (1,1,7,2.0,TO_DATE('2024-01-10','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (2,3,6,1.0,TO_DATE('2024-02-05','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (3,3,8,5.0,TO_DATE('2024-02-05','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (4,5,1,1.5,TO_DATE('2024-03-03','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (5,5,10,2.0,TO_DATE('2024-03-03','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (6,8,1,1.0,TO_DATE('2024-04-15','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (7,8,2,0.5,TO_DATE('2024-04-15','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (8,9,6,2.0,TO_DATE('2024-05-06','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (9,9,9,1.0,TO_DATE('2024-05-06','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (10,13,3,100.0,TO_DATE('2024-07-01','YYYY-MM-DD'))",
    "INSERT INTO UTILIZARI_MATERIALE VALUES (11,13,4,1.0,TO_DATE('2024-07-01','YYYY-MM-DD'))",
]
istoric = [
    "INSERT INTO ISTORIC_MEDICAL VALUES (1,1,1,1,'Carie medie la dintele 16. Stare generala buna a danturii.','Obturatie compozit si detartraj la urmatoarea vizita',TO_DATE('2024-01-10','YYYY-MM-DD'),NULL)",
    "INSERT INTO ISTORIC_MEDICAL VALUES (2,2,2,2,'Malocluzie de clasa II. Indicate tratament ortodontic.','Aparat fix metalic sau ceramic, durata estimata 18 luni',TO_DATE('2024-01-15','YYYY-MM-DD'),NULL)",
    "INSERT INTO ISTORIC_MEDICAL VALUES (3,3,3,3,'Molar 3 inferior stang inclus partial. Pericoronarita recurenta.','Extractie chirurgicala molar 3',TO_DATE('2024-02-05','YYYY-MM-DD'),NULL)",
    "INSERT INTO ISTORIC_MEDICAL VALUES (4,4,5,4,'Dinti cu coloratii intrinseci. Pacienta doreste estetica superioara.','Albire dentara, eventual fatete ceramice',TO_DATE('2024-02-20','YYYY-MM-DD'),NULL)",
    "INSERT INTO ISTORIC_MEDICAL VALUES (5,10,5,10,'Coloratii extrinseci semnificative. Pacientul fumeaza.','Albire profesionala, renuntare la fumat',TO_DATE('2024-05-20','YYYY-MM-DD'),NULL)",
    "INSERT INTO ISTORIC_MEDICAL VALUES (6,10,4,13,'Dinte 36 cu necroza pulpara. Necesita tratament endodontic.','Tratament canal si coroana de acoperire',TO_DATE('2024-07-01','YYYY-MM-DD'),NULL)",
]

all_dml = cabinete+medici+asistente+pacienti+servicii+materiale+programari+ps+facturi+utilizari+istoric
ok, err = run(conn_oltp, all_dml, "DML")
print(f"\nRezultat: {ok} OK, {err} erori")

print("\n=== VERIFICARE FINALA ===")
c = conn_oltp()
cur = c.cursor()
total_ok = True
expected = {"CABINETE":5,"MEDICI":5,"ASISTENTE":3,"PACIENTI":10,"SERVICII":18,
            "MATERIALE":10,"PROGRAMARI":35,"PROGRAMARI_SERVICII":39,
            "FACTURI":33,"UTILIZARI_MATERIALE":11,"ISTORIC_MEDICAL":6}
for t, exp in expected.items():
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    status = "✅" if cnt == exp else f"❌ (asteptat {exp})"
    print(f"  {t}: {cnt} {status}")
    if cnt != exp: total_ok = False
c.close()

if total_ok:
    print("\n✅ PERFECT! Acum ruleaza aplicatia:")
    print("   python app/app.py")
else:
    print("\n⚠️  Unele tabele au date incomplete — verifica erorile de mai sus.")
