from flask import Flask, request
import psycopg2
from datetime import date, datetime, timedelta
import sys
from flask import render_template, request,jsonify
import base64
import requests
import json
from statistics import mean

TTN_API_KEY = "NNSXS.DUM7N4ASGAZURRE2NQE6HWZ7LFIEIA4UVPYFBHY.USJFGP6JCIPRRS5QHHBOYUJ5ZLYCSR5TXMEIYET6LC7Q2YTP2NCA"


APPLICATION_ID = "tudor"
DEVICE_ID = "smart-sleeping"
TTN_REGION = "eu1"


sys.stdout.reconfigure(encoding='utf-8')
app = Flask(__name__)

# Connexion à PostgreSQL
def get_conn():
    return psycopg2.connect(
        dbname="sommeil",
        user="postgres",
        password="necPA459",
        host="localhost",
        port="5432"
    )

# Route Webhook TTN
@app.route("/ttn", methods=["POST"])
def ttn_hook():
    data = request.json
    print("📦 Donnée brute reçue :", data)

    try:
        payload = data["uplink_message"]["decoded_payload"]

        timestamp = datetime.utcnow()
        temp = payload.get("temperature", 0)
        hum = payload.get("humidity", 0)
        amb = payload.get("temp_amb", None)
        obj = payload.get("temp_obj", None)
        presence = payload.get("presence", False)
        weight = payload.get("weight", 0)
        bpm = payload.get("bpm", None)


        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mesures (timestamp, temperature, humidity, temp_amb, temp_obj, presence, weight, bpm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (timestamp, temp, hum, amb, obj, presence, weight, bpm))

        conn.commit()
        cur.close()
        conn.close()

        print(f"Mesure stockée : {timestamp} | Temp : {temp} | Hum : {hum}")
        return {"status": "ok"}

    except Exception as e:
        print("Erreur :", e)
        return {"status": "error", "detail": str(e)}, 400

from flask import render_template
from datetime import timedelta

@app.route("/analyse/<int:n>")
def analyse_nuit(n):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, temperature, humidity, presence, weight, bpm, temp_obj
        FROM mesures
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Détermine la plage correspondant à la nuit n
    if len(rows) < (n - 1) * 150:
        return f"Pas assez de données pour la nuit {n}", 404

    debut = (n - 1) * 150
    fin = debut + 150
    sous_ensemble = rows[debut:fin]

    # Prépare les données à envoyer au template
    import json
    context = {
        "nuit_num": n,
        "heures": json.dumps([r[0].strftime("%H:%M") for r in sous_ensemble]),
        "temp": json.dumps([r[1] for r in sous_ensemble]),
        "humidity": json.dumps([r[2] for r in sous_ensemble]),
        "presence": json.dumps([r[3] for r in sous_ensemble]),
        "weight": json.dumps([r[4] for r in sous_ensemble]),
        "bpm": json.dumps([r[5] for r in sous_ensemble])
    }
    return render_template("nuit.html", **context)





@app.route("/data", methods=["GET"])
def get_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, temperature, humidity, temp_amb, temp_obj, presence, weight, bpm FROM mesures ORDER BY timestamp DESC LIMIT 100")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = [
        {
        "timestamp": row[0].isoformat(),
        "temperature": row[1],
        "humidity": row[2],
        "temp_amb": row[3],
        "temp_obj": row[4],
        "presence": row[5],
        "weight": row[6],
        "bpm": row[7]
        }

        for row in rows
    ]
    return {"data": data}

import json
from decimal import Decimal


@app.route("/dashboard")
def dashboard():
    conn = get_conn()
    cur = conn.cursor()
    
    # Récupération des paramètres start et end de l'URL
    start_date = request.args.get('start', (date.today() - timedelta(days=7)).isoformat())
    end_date = request.args.get('end', date.today().isoformat())

    print(f"Plage de dates sélectionnée : {start_date} → {end_date}")

    # Requête dynamique sur la période choisie
    cur.execute("""
        SELECT 
            DATE(timestamp) AS date_nuit,
            ROUND(AVG(temperature), 1) AS temp_moy,
            ROUND(AVG(bpm), 1) AS bpm_moy,
            ROUND(AVG(humidity), 1) AS hum_moy
        FROM mesures
        WHERE DATE(timestamp) BETWEEN %s AND %s
        GROUP BY DATE(timestamp)
        ORDER BY date_nuit ASC
    """, (start_date, end_date))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Préparation des listes pour le graphique
    jours = [row[0].strftime("%d/%m") for row in rows]
    moyennes_temp = [float(row[1]) if row[1] else 0 for row in rows]
    moyennes_bpm = [float(row[2]) if row[2] else 0 for row in rows]
    moyennes_hum = [float(row[3]) if row[3] else 0 for row in rows]

    # Calcul des moyennes globales (par exemple pour affichage en haut)
    moyenne_temp = round(sum(moyennes_temp) / len(moyennes_temp), 1) if moyennes_temp else 0
    moyenne_bpm = round(sum(moyennes_bpm) / len(moyennes_bpm), 1) if moyennes_bpm else 0
    moyenne_hum = round(sum(moyennes_hum) / len(moyennes_hum), 1) if moyennes_hum else 0

    # Contexte envoyé au template
    context = {
        "jours": json.dumps(jours),
        "moyennes_temp": json.dumps(moyennes_temp),
        "moyennes_bpm": json.dumps(moyennes_bpm),
        "moyennes_hum": json.dumps(moyennes_hum),
        "moyenne_temp": moyenne_temp,
        "moyenne_bpm": moyenne_bpm,
        "moyenne_hum": moyenne_hum,
        "start_date": start_date,
        "end_date": end_date
    }

    return render_template("dashboard.html", **context)




@app.route("/analyse")
def analyse():
    return render_template("analyse.html")

@app.route("/deepsite_data")
def deepsite_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, temperature, humidity, temp_amb, temp_obj, presence, weight, bpm
        FROM mesures
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "timestamp": row[0].isoformat(),
            "temperature": row[1],
            "humidity": row[2],
            "temp_amb": row[3],
            "temp_obj": row[4],
            "presence": row[5],
            "weight": row[6],
            "bpm": row[7],
        })
    return jsonify(data)

@app.route("/deepsite")
def deepsite():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, temperature, bpm, presence
        FROM mesures
        WHERE timestamp > NOW() - INTERVAL '1 day'
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return "Pas de données disponibles", 404



    timestamps = [r[0] for r in rows]
    temperatures = [r[1] for r in rows if r[1] is not None]
    bpm_values = [r[2] for r in rows if r[2] is not None]
    presences = [r[3] for r in rows]

    sleep_quality = 87  # À calculer plus finement si besoin
    heart_rate_avg = int(mean(bpm_values))
    temperature_avg = round(mean(temperatures), 1)
    sleep_duration = round(len([p for p in presences if p]) * 5 / 60, 1)
    start_time = timestamps[0].strftime("%I:%M %p")
    end_time = timestamps[-1].strftime("%I:%M %p")

    return render_template("deepsite.html",
        sleep_quality=sleep_quality,
        heart_rate_avg=heart_rate_avg,
        temperature_avg=temperature_avg,
        sleep_duration=sleep_duration,
        start_time=start_time,
        end_time=end_time
    )

@app.route("/analyse_json")
def analyse_json():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, temperature, humidity, temp_amb, temp_obj, presence, weight, bpm
        FROM mesures
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Convertir en liste de dicts
    mesures = []
    for row in rows:
        mesures.append({
            "timestamp": row[0].isoformat(),
            "temperature": row[1],
            "humidity": row[2],
            "temp_amb": row[3],
            "temp_obj": row[4],
            "presence": row[5],
            "weight": row[6],
            "bpm": row[7]
        })

    # Score simple
    score = 100
    mouvements = [m["presence"] for m in mesures if m["presence"]]
    temp_penalties = [m for m in mesures if m["temp_amb"] and (m["temp_amb"] < 18 or m["temp_amb"] > 23)]
    score -= len(temp_penalties) * 0.5
    score -= len(mouvements) * 0.3
    score = max(0, round(score))

    # Hypnogramme simplifié
    def detecter_phase(m):
        if m["presence"] == False:
            return ("Absent", 0)
        elif m["temp_obj"] and m["temp_obj"] < 32:
            return ("Profond", 3)
        elif m["presence"] == True and m["temp_obj"] and m["temp_obj"] > 35:
            return ("Agité", 1)
        else:
            return ("Léger", 2)

    hypnogramme = []
    for m in mesures:
        phase_label, phase_num = detecter_phase(m)
        hypnogramme.append({
            "timestamp": m["timestamp"],
            "phase": phase_label,
            "phase_numerique": phase_num,
            "temp_amb": m["temp_amb"],
            "humidity": m["humidity"],
            "bpm": m["bpm"]
        })

    # Conseils personnalisés simples
    conseils = []
    if len(temp_penalties) > 0:
        conseils.append("La température ambiante dépasse la zone idéale (18–23°C).")
    if len(mouvements) > 5:
        conseils.append("Sommeil agité détecté : essayez d’éviter les écrans avant de dormir.")
    if score < 70:
        conseils.append("Votre score de sommeil est faible. Essayez une routine plus relaxante.")
    if not conseils:
        conseils.append("Très bon sommeil, continuez comme ça !")

    return {
        "score": score,
        "hypnogramme": hypnogramme,
        "conseils": conseils
    }

@app.route("/dashboard_data")
def dashboard_data():
    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"error": "start and end required"}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            DATE(timestamp) AS date_nuit,
            ROUND(AVG(temperature), 1),
            ROUND(AVG(bpm), 1)
        FROM mesures
        WHERE timestamp >= %s AND timestamp <= %s
        GROUP BY DATE(timestamp)
        ORDER BY date_nuit
    """, (start, end))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({
        "dates": [],
        "temp": [],
        "bpm": []
    })


    result = {
        "dates": [r[0].strftime("%d/%m") for r in rows],
        "temp": [float(r[1]) for r in rows],
        "bpm": [float(r[2]) for r in rows]
    }
    print("Start:", start)
    print("End:", end)

    return jsonify(result)

@app.route("/send_alarm", methods=["POST"])
def send_alarm():
    try:
        heure = int(request.json["hour"])
        minute = int(request.json["minute"])

        if not (0 <= heure <= 23 and 0 <= minute <= 59):
            return jsonify({"error": "Heure invalide"}), 400

        payload_bytes = bytes([heure, minute])
        payload_b64 = base64.b64encode(payload_bytes).decode("utf-8")

        url = f"https://{TTN_REGION}.cloud.thethings.network/api/v3/as/applications/{APPLICATION_ID}/devices/{DEVICE_ID}/down/push"
        headers = {
            "Authorization": f"Bearer {TTN_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "downlinks": [{
                "f_port": 1,
                "frm_payload": payload_b64,
                "priority": "NORMAL"
            }]
        }

        res = requests.post(url, json=body, headers=headers)
        if res.status_code in [200, 202]:
            return jsonify({"status": "ok", "payload": payload_b64})
        else:
            return jsonify({"error": "TTN error", "response": res.text}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)