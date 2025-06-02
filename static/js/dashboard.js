let chart = null;

function updateGraph() {
  const start = document.getElementById("startDate").value;
  const end = document.getElementById("endDate").value;
  if (start && end) {
    window.location.href = `/dashboard?start=${start}&end=${end}`;
  } else {
    alert("Veuillez choisir une plage de dates valide !");
  }
}


document.getElementById("alarmForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const hour = parseInt(document.getElementById("alarmHour").value);
    const minute = parseInt(document.getElementById("alarmMinute").value);
  
    const res = await fetch("/send_alarm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hour, minute })
    });
  
    const result = await res.json();
    const status = document.getElementById("alarmStatus");
  
    if (res.ok) {
      status.textContent = `⏰ Alarme envoyée à ${hour}h${minute.toString().padStart(2, "0")} (payload : ${result.payload})`;
      status.style.color = "green";
    } else {
      status.textContent = "❌ Erreur : " + (result.error || "Échec envoi TTN");
      status.style.color = "red";
    }
  });
  