"""Aplicatia web: CRUD OLTP, panou ETL si rapoarte din DW.

Pornire: python app/app.py
"""

import json
import os
import sys
from datetime import datetime, date

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Permite importul pachetului etl din radacina proiectului
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.config import connect_dw as get_dw_conn  # noqa: E402
from etl.config import connect_oltp as get_oltp_conn  # noqa: E402

app = Flask(__name__)

# Fara FLASK_SECRET_KEY se genereaza o cheie aleatoare la fiecare pornire
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

def rows_to_dicts(cursor):
    cols = [d[0].lower() for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def format_date(d):
    if isinstance(d, (datetime, date)):
        return d.strftime('%Y-%m-%d')
    return str(d) if d else ''


def report_error(exc):
    """Eroare generica pentru client; detaliile raman doar in log."""
    app.logger.exception("Interogarea raportului a esuat")
    return jsonify({'eroare': 'A raportarea esuat. Contactati administratorul.'}), 500

@app.route('/')
def index():
    return render_template('index.html')

# ============================================================
# MODUL 1: CRUD OLTP - PACIENTI
# ============================================================

@app.route('/oltp/pacienti')
def pacienti_list():
    try:
        conn = get_oltp_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT ID_PACIENT, NUME, PRENUME, CNP,
                   TO_CHAR(DATA_NASTERII,'DD.MM.YYYY') AS DATA_NASTERII,
                   TELEFON, EMAIL, ORAS, JUDET, ACTIV
            FROM PACIENTI
            ORDER BY NUME, PRENUME
        """)
        pacienti = rows_to_dicts(cur)
        conn.close()
        return render_template('pacienti_list.html', pacienti=pacienti)
    except Exception as e:
        flash(f'Eroare: {e}', 'danger')
        return render_template('pacienti_list.html', pacienti=[])

@app.route('/oltp/pacienti/nou', methods=['GET','POST'])
def pacient_nou():
    if request.method == 'POST':
        try:
            conn = get_oltp_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO PACIENTI (ID_PACIENT, NUME, PRENUME, CNP, DATA_NASTERII,
                    TELEFON, EMAIL, ADRESA, ORAS, JUDET, ACTIV)
                VALUES (NULL, :1, :2, :3, TO_DATE(:4,'YYYY-MM-DD'), :5, :6, :7, :8, :9, 'Y')
            """, (
                request.form['nume'], request.form['prenume'],
                request.form.get('cnp') or None,
                request.form.get('data_nasterii') or None,
                request.form.get('telefon'), request.form.get('email'),
                request.form.get('adresa'), request.form.get('oras','Bucuresti'),
                request.form.get('judet','Ilfov')
            ))
            conn.commit(); conn.close()
            flash('Pacient adaugat cu succes!', 'success')
            return redirect(url_for('pacienti_list'))
        except Exception as e:
            flash(f'Eroare la adaugare: {e}', 'danger')
    return render_template('pacient_form.html', pacient=None, action='Adauga')

@app.route('/oltp/pacienti/<int:id>/edit', methods=['GET','POST'])
def pacient_edit(id):
    try:
        conn = get_oltp_conn()
        cur = conn.cursor()
        if request.method == 'POST':
            cur.execute("""
                UPDATE PACIENTI SET NUME=:1, PRENUME=:2, CNP=:3,
                    DATA_NASTERII=TO_DATE(:4,'YYYY-MM-DD'),
                    TELEFON=:5, EMAIL=:6, ADRESA=:7, ORAS=:8, JUDET=:9
                WHERE ID_PACIENT=:10
            """, (
                request.form['nume'], request.form['prenume'],
                request.form.get('cnp') or None,
                request.form.get('data_nasterii') or None,
                request.form.get('telefon'), request.form.get('email'),
                request.form.get('adresa'), request.form.get('oras'),
                request.form.get('judet'), id
            ))
            conn.commit(); conn.close()
            flash('Pacient actualizat!', 'success')
            return redirect(url_for('pacienti_list'))
        cur.execute("""
            SELECT ID_PACIENT, NUME, PRENUME, CNP,
                   TO_CHAR(DATA_NASTERII,'YYYY-MM-DD') AS DATA_NASTERII,
                   TELEFON, EMAIL, ADRESA, ORAS, JUDET
            FROM PACIENTI WHERE ID_PACIENT=:1
        """, (id,))
        pacient = rows_to_dicts(cur)
        conn.close()
        if not pacient: flash('Pacient negasit', 'warning'); return redirect(url_for('pacienti_list'))
        return render_template('pacient_form.html', pacient=pacient[0], action='Editeaza')
    except Exception as e:
        flash(f'Eroare: {e}', 'danger')
        return redirect(url_for('pacienti_list'))

@app.route('/oltp/pacienti/<int:id>/delete', methods=['POST'])
def pacient_delete(id):
    try:
        conn = get_oltp_conn()
        cur = conn.cursor()
        cur.execute("UPDATE PACIENTI SET ACTIV='N' WHERE ID_PACIENT=:1", (id,))
        conn.commit(); conn.close()
        flash('Pacient dezactivat!', 'success')
    except Exception as e:
        flash(f'Eroare la stergere: {e}', 'danger')
    return redirect(url_for('pacienti_list'))

# ============================================================
# MODUL 1: CRUD PROGRAMARI
# ============================================================

@app.route('/oltp/programari')
def programari_list():
    try:
        conn = get_oltp_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.ID_PROGRAMARE,
                   pac.NUME||' '||pac.PRENUME AS PACIENT,
                   m.NUME||' '||m.PRENUME AS MEDIC,
                   m.SPECIALIZARE,
                   c.DENUMIRE AS CABINET,
                   TO_CHAR(p.DATA_PROG,'DD.MM.YYYY') AS DATA_PROG,
                   p.ORA_START, p.STATUS,
                   NVL(f.TOTAL,0) AS TOTAL_FACTURA,
                   NVL(f.STATUS_PLATA,'N/A') AS STATUS_PLATA
            FROM PROGRAMARI p
            JOIN PACIENTI pac ON pac.ID_PACIENT=p.ID_PACIENT
            JOIN MEDICI m      ON m.ID_MEDIC=p.ID_MEDIC
            JOIN CABINETE c    ON c.ID_CABINET=p.ID_CABINET
            LEFT JOIN FACTURI f ON f.ID_PROGRAMARE=p.ID_PROGRAMARE
            ORDER BY p.DATA_PROG DESC, p.ORA_START
        """)
        programari = rows_to_dicts(cur)
        conn.close()
        return render_template('programari_list.html', programari=programari)
    except Exception as e:
        flash(f'Eroare: {e}', 'danger')
        return render_template('programari_list.html', programari=[])

@app.route('/oltp/programari/noua', methods=['GET','POST'])
def programare_noua():
    try:
        conn = get_oltp_conn()
        cur = conn.cursor()
        if request.method == 'POST':
            cur.execute("""
                INSERT INTO PROGRAMARI (ID_PROGRAMARE, ID_PACIENT, ID_MEDIC, ID_CABINET,
                    DATA_PROG, ORA_START, ORA_SFARSIT, STATUS, OBSERVATII)
                VALUES (NULL,:1,:2,:3,TO_DATE(:4,'YYYY-MM-DD'),:5,:6,:7,:8)
            """, (
                int(request.form['id_pacient']), int(request.form['id_medic']),
                int(request.form['id_cabinet']), request.form['data_prog'],
                request.form['ora_start'], request.form.get('ora_sfarsit'),
                request.form.get('status','Programata'), request.form.get('observatii')
            ))
            conn.commit()
            flash('Programare adaugata!', 'success')
            conn.close()
            return redirect(url_for('programari_list'))
        cur.execute("SELECT ID_PACIENT, NUME||' '||PRENUME AS LABEL FROM PACIENTI WHERE ACTIV='Y' ORDER BY NUME")
        pacienti = rows_to_dicts(cur)
        cur.execute("SELECT ID_MEDIC, NUME||' '||PRENUME||' ('||SPECIALIZARE||')' AS LABEL FROM MEDICI WHERE ACTIV='Y' ORDER BY SPECIALIZARE")
        medici = rows_to_dicts(cur)
        cur.execute("SELECT ID_CABINET, DENUMIRE AS LABEL FROM CABINETE WHERE ACTIV='Y' ORDER BY DENUMIRE")
        cabinete = rows_to_dicts(cur)
        conn.close()
        return render_template('programare_form.html', pacienti=pacienti, medici=medici, cabinete=cabinete)
    except Exception as e:
        flash(f'Eroare: {e}', 'danger')
        return redirect(url_for('programari_list'))

# ============================================================
# MODUL 2: PROPAGARE OLTP -> DW (ETL)
# ============================================================

@app.route('/etl')
def etl_dashboard():
    stats = {}
    try:
        oltp = get_oltp_conn(); dw = get_dw_conn()
        c1 = oltp.cursor(); c2 = dw.cursor()

        c1.execute("SELECT COUNT(*) FROM PROGRAMARI WHERE STATUS='Finalizata'")
        stats['oltp_prog_finalizate'] = c1.fetchone()[0]

        c1.execute("SELECT COUNT(*) FROM PROGRAMARI_SERVICII ps JOIN PROGRAMARI p ON p.ID_PROGRAMARE=ps.ID_PROGRAMARE WHERE p.STATUS='Finalizata'")
        stats['oltp_servicii_efectuate'] = c1.fetchone()[0]

        c2.execute("SELECT COUNT(*) FROM FAPTE_SERVICII")
        stats['dw_fapte'] = c2.fetchone()[0]

        c1.execute("SELECT COUNT(*) FROM PACIENTI"); stats['oltp_pacienti'] = c1.fetchone()[0]
        c2.execute("SELECT COUNT(*) FROM DIM_PACIENTI"); stats['dw_pacienti'] = c2.fetchone()[0]

        c2.execute("SELECT MAX(TIMP_ID) FROM FAPTE_SERVICII")
        r = c2.fetchone()[0]
        stats['dw_ultima_data'] = format_date(r) if r else 'N/A'

        stats['diferenta'] = stats['oltp_servicii_efectuate'] - stats['dw_fapte']
        oltp.close(); dw.close()
    except Exception as e:
        stats['eroare'] = str(e)
    return render_template('etl_dashboard.html', stats=stats)

@app.route('/etl/run', methods=['POST'])
def etl_run():
    """Executa ETL incremental: adauga in DW faptele noi din OLTP"""
    try:
        oltp = get_oltp_conn(); dw = get_dw_conn()
        c_oltp = oltp.cursor(); c_dw = dw.cursor()

        c_dw.execute("SELECT NVL(MAX(TIMP_ID), TO_DATE('2000-01-01','YYYY-MM-DD')) FROM FAPTE_SERVICII")
        ultima_data = c_dw.fetchone()[0]

        c_oltp.execute("""
            SELECT
                TRUNC(pr.DATA_PROG) AS data_prog,
                pr.ID_PACIENT, pr.ID_MEDIC, pr.ID_CABINET,
                ps.ID_SERVICIU, ps.CANTITATE, ps.PRET_APLICAT, ps.DISCOUNT_PROC,
                pr.ID_PROGRAMARE, f.ID_FACTURA, f.METODA_PLATA,
                pac.ORAS, pac.JUDET
            FROM PROGRAMARI_SERVICII ps
            JOIN PROGRAMARI pr ON pr.ID_PROGRAMARE = ps.ID_PROGRAMARE
            JOIN FACTURI f     ON f.ID_PROGRAMARE  = pr.ID_PROGRAMARE
            JOIN PACIENTI pac  ON pac.ID_PACIENT   = pr.ID_PACIENT
            WHERE pr.STATUS = 'Finalizata'
              AND TRUNC(pr.DATA_PROG) > :ultima_data
        """, ultima_data=ultima_data)
        noi = c_oltp.fetchall()

        inserate = 0
        for row in noi:
            data_prog, id_pac, id_med, id_cab, id_serv, cant, pret, disc, id_prog, id_fact, metoda, oras, judet = row

            c_dw.execute("SELECT ID_PACIENT_DW FROM DIM_PACIENTI WHERE ID_PACIENT_OLTP=:1 AND ACTIV='Y'", (id_pac,))
            r = c_dw.fetchone(); pacient_dw = r[0] if r else 1

            c_dw.execute("SELECT ID_MEDIC_DW FROM DIM_MEDICI WHERE ID_MEDIC_OLTP=:1", (id_med,))
            r = c_dw.fetchone(); medic_dw = r[0] if r else 1

            c_dw.execute("SELECT ID_SERVICIU_DW FROM DIM_SERVICII WHERE ID_SERVICIU_OLTP=:1", (id_serv,))
            r = c_dw.fetchone(); serviciu_dw = r[0] if r else 1

            c_dw.execute("SELECT ID_CABINET_DW FROM DIM_CABINETE WHERE ID_CABINET_OLTP=:1", (id_cab,))
            r = c_dw.fetchone(); cabinet_dw = r[0] if r else 1

            c_dw.execute("SELECT ID_LOCATIE FROM DIM_LOCATIE WHERE ORAS=:1 AND JUDET=:2", (oras, judet))
            r = c_dw.fetchone(); locatie_dw = r[0] if r else 1

            c_dw.execute("SELECT ID_METODA FROM DIM_METODA_PLATA WHERE DENUMIRE=:1", (metoda,))
            r = c_dw.fetchone(); metoda_dw = r[0] if r else 0

            subtotal = round(cant * pret * (1 - (disc or 0)/100), 2)
            tva = round(subtotal * 0.19, 2)
            total = round(subtotal * 1.19, 2)

            c_dw.execute("SELECT seq_dw_fapte.NEXTVAL FROM DUAL")
            new_id = c_dw.fetchone()[0]

            c_dw.execute("""
                INSERT INTO FAPTE_SERVICII VALUES (
                    :1, :2, :3, :4, :5, :6, :7, :8, :9, :10,
                    :11, :12, :13, :14, :15, :16, :17
                )
            """, (new_id, data_prog, pacient_dw, medic_dw, serviciu_dw,
                  cabinet_dw, locatie_dw, metoda_dw, id_prog, id_fact,
                  cant, pret, disc or 0, subtotal, tva, total, 0))
            inserate += 1

        dw.commit(); oltp.close(); dw.close()
        return jsonify({'success': True, 'inserate': inserate,
                        'mesaj': f'{inserate} fapte noi propagate din OLTP in DW'})
    except Exception as e:
        return jsonify({'success': False, 'eroare': str(e)})

# ============================================================
# MODUL 3: RAPOARTE GRAFICE DINAMICE
# ============================================================

@app.route('/rapoarte')
def rapoarte():
    return render_template('rapoarte.html')

@app.route('/api/raport1')
def api_raport1():
    """Venituri lunare pe categorii (ROLLUP)"""
    an = request.args.get('an', '2024')
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT dt.LUNA, dt.LUNA_NUME,
                   ds.CATEGORIE,
                   SUM(f.TOTAL_CU_TVA) AS VENIT_TOTAL
            FROM FAPTE_SERVICII f
            JOIN DIM_TIMP     dt ON dt.ID_TIMP        = f.TIMP_ID
            JOIN DIM_SERVICII ds ON ds.ID_SERVICIU_DW = f.SERVICIU_ID
            WHERE dt.AN = :1
            GROUP BY dt.LUNA, dt.LUNA_NUME, ds.CATEGORIE
            ORDER BY dt.LUNA, ds.CATEGORIE
        """, (int(an),))
        rows = rows_to_dicts(cur)
        dw.close()
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

@app.route('/api/raport2')
def api_raport2():
    """Performanta medici"""
    an = request.args.get('an', '2024')
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT dm.NUME||' '||dm.PRENUME AS MEDIC,
                   dm.SPECIALIZARE,
                   COUNT(DISTINCT f.ID_PROGRAMARE_OLTP) AS NR_PROGRAMARI,
                   COUNT(f.ID_FAPT)                     AS NR_SERVICII,
                   ROUND(SUM(f.TOTAL_CU_TVA),2)         AS VENIT_TOTAL,
                   ROUND(AVG(f.PRET_UNITAR),2)          AS PRET_MEDIU
            FROM FAPTE_SERVICII f
            JOIN DIM_MEDICI dm ON dm.ID_MEDIC_DW = f.MEDIC_ID
            JOIN DIM_TIMP   dt ON dt.ID_TIMP      = f.TIMP_ID
            WHERE dt.AN = :1
            GROUP BY dm.ID_MEDIC_DW, dm.NUME, dm.PRENUME, dm.SPECIALIZARE
            ORDER BY VENIT_TOTAL DESC
        """, (int(an),))
        rows = rows_to_dicts(cur)
        dw.close()
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

@app.route('/api/raport3')
def api_raport3():
    """Evolutia lunara cu variatie"""
    an = request.args.get('an', '2024')
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT dt.LUNA, dt.LUNA_NUME, dt.TRIMESTRU,
                   ROUND(SUM(f.TOTAL_CU_TVA),2)  AS VENIT_LUNA,
                   COUNT(f.ID_FAPT)              AS NR_SERVICII
            FROM FAPTE_SERVICII f
            JOIN DIM_TIMP dt ON dt.ID_TIMP = f.TIMP_ID
            WHERE dt.AN = :1
            GROUP BY dt.LUNA, dt.LUNA_NUME, dt.TRIMESTRU
            ORDER BY dt.LUNA
        """, (int(an),))
        rows = rows_to_dicts(cur)
        dw.close()
        for i, r in enumerate(rows):
            if i > 0:
                prev = rows[i-1]['venit_luna'] or 0
                curr = r['venit_luna'] or 0
                r['variatie_pct'] = round((curr - prev) / prev * 100, 2) if prev else 0
            else:
                r['variatie_pct'] = 0
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

@app.route('/api/raport4')
def api_raport4():
    """Segmentare pacienti"""
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT dp.NUME||' '||dp.PRENUME AS PACIENT,
                   dp.ORAS, dp.GRUPA_VARSTA,
                   COUNT(DISTINCT f.ID_PROGRAMARE_OLTP) AS NR_VIZITE,
                   ROUND(SUM(f.TOTAL_CU_TVA),2)         AS CHELTUIELI_TOTALE
            FROM FAPTE_SERVICII  f
            JOIN DIM_PACIENTI dp ON dp.ID_PACIENT_DW = f.PACIENT_ID
            GROUP BY dp.ID_PACIENT_DW, dp.NUME, dp.PRENUME, dp.ORAS, dp.GRUPA_VARSTA
            ORDER BY CHELTUIELI_TOTALE DESC
        """)
        rows = rows_to_dicts(cur)
        dw.close()
        n = len(rows)
        for i, r in enumerate(rows):
            q = int(i / n * 4) + 1 if n > 0 else 4
            q = min(q, 4)
            r['segment'] = ['VIP','Premium','Standard','Basic'][q-1]
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

@app.route('/api/raport5')
def api_raport5():
    """Utilizare cabinete"""
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT dc.DENUMIRE AS CABINET, dc.TIP_CABINET,
                   dt.AN,
                   COUNT(DISTINCT f.ID_PROGRAMARE_OLTP) AS NR_PROGRAMARI,
                   ROUND(SUM(f.TOTAL_CU_TVA),2)         AS VENIT_TOTAL
            FROM FAPTE_SERVICII  f
            JOIN DIM_CABINETE dc ON dc.ID_CABINET_DW = f.CABINET_ID
            JOIN DIM_TIMP     dt ON dt.ID_TIMP        = f.TIMP_ID
            GROUP BY dc.DENUMIRE, dc.TIP_CABINET, dt.AN
            ORDER BY dc.DENUMIRE, dt.AN
        """)
        rows = rows_to_dicts(cur)
        dw.close()
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

@app.route('/api/raport6')
def api_raport6():
    """Top servicii per categorie"""
    try:
        dw = get_dw_conn(); cur = dw.cursor()
        cur.execute("""
            SELECT CATEGORIE, DENUMIRE,
                   NR_EFECTUAT, ROUND(VENIT_TOTAL,2) AS VENIT_TOTAL, RANK_IN_CAT
            FROM (
                SELECT ds.CATEGORIE, ds.DENUMIRE,
                       COUNT(f.ID_FAPT)     AS NR_EFECTUAT,
                       SUM(f.TOTAL_CU_TVA)  AS VENIT_TOTAL,
                       DENSE_RANK() OVER (
                           PARTITION BY ds.CATEGORIE
                           ORDER BY SUM(f.TOTAL_CU_TVA) DESC
                       ) AS RANK_IN_CAT
                FROM FAPTE_SERVICII  f
                JOIN DIM_SERVICII ds ON ds.ID_SERVICIU_DW = f.SERVICIU_ID
                GROUP BY ds.CATEGORIE, ds.DENUMIRE
            )
            WHERE RANK_IN_CAT <= 3
            ORDER BY CATEGORIE, RANK_IN_CAT
        """)
        rows = rows_to_dicts(cur)
        dw.close()
        return jsonify(rows)
    except Exception as e:
        return report_error(e)

if __name__ == '__main__':
    # 5000 e ocupat pe macOS de AirPlay Receiver
    port = int(os.getenv("FLASK_PORT", "5001"))
    # Doar loopback implicit: debugger-ul Werkzeug permite executie de cod
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    print("=" * 60)
    print("  DW Clinica Stomatologica - Aplicatie Web")
    print(f"  Acceseaza: http://localhost:{port}")
    print("=" * 60)
    app.run(debug=debug, host=host, port=port)
