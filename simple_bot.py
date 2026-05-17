<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦂 BY LUIS R - IPTV Info</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --gold: #FFD700;
    --gold2: #FFA500;
    --dark: #0a0a0f;
    --dark2: #0f0f1a;
    --card: #12121f;
    --card2: #1a1a2e;
    --neon-green: #00ff88;
    --neon-red: #ff3366;
    --neon-blue: #00cfff;
    --border: rgba(255,215,0,0.25);
    --text: #e8e8f0;
    --dim: #8888aa;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--dark);
    font-family: 'Exo 2', sans-serif;
    color: var(--text);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse at 20% 0%, rgba(255,165,0,0.07) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 100%, rgba(0,207,255,0.06) 0%, transparent 50%),
      repeating-linear-gradient(
        0deg,
        transparent,
        transparent 40px,
        rgba(255,255,255,0.012) 40px,
        rgba(255,255,255,0.012) 41px
      ),
      repeating-linear-gradient(
        90deg,
        transparent,
        transparent 40px,
        rgba(255,255,255,0.012) 40px,
        rgba(255,255,255,0.012) 41px
      );
    padding: 20px 10px 40px;
  }

  .wrapper {
    max-width: 600px;
    margin: 0 auto;
  }

  /* ─── HEADER ─── */
  .header {
    text-align: center;
    padding: 28px 20px 20px;
    position: relative;
    margin-bottom: 6px;
  }
  .header::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,165,0,0.08), rgba(0,207,255,0.06));
    border-radius: 18px 18px 0 0;
    border: 1px solid var(--border);
    border-bottom: none;
  }
  .scorpion-title {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 3px;
    color: var(--gold);
    text-transform: uppercase;
    position: relative;
    text-shadow: 0 0 20px rgba(255,215,0,0.5);
    animation: pulse-gold 3s ease-in-out infinite;
  }
  @keyframes pulse-gold {
    0%,100% { text-shadow: 0 0 20px rgba(255,215,0,0.5); }
    50% { text-shadow: 0 0 35px rgba(255,215,0,0.9), 0 0 60px rgba(255,165,0,0.4); }
  }
  .main-title {
    font-family: 'Orbitron', monospace;
    font-size: clamp(14px, 4vw, 20px);
    font-weight: 900;
    color: #fff;
    letter-spacing: 2px;
    margin: 8px 0 4px;
    position: relative;
    text-shadow: 0 0 30px rgba(0,207,255,0.4);
  }
  .divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold), var(--neon-blue), var(--gold), transparent);
    margin: 14px 0;
    animation: shimmer 2.5s linear infinite;
    background-size: 200% 100%;
  }
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }

  /* ─── CARDS ─── */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    margin-bottom: 10px;
    overflow: hidden;
    position: relative;
    transition: border-color 0.3s;
  }
  .card:hover { border-color: rgba(255,215,0,0.5); }
  .card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--gold2), var(--neon-blue), var(--gold2));
    background-size: 200% 100%;
    animation: shimmer 2s linear infinite;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
  }
  .card-header-icon { font-size: 18px; }
  .card-header-title {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2.5px;
    color: var(--gold);
    text-transform: uppercase;
    flex: 1;
  }
  .card-header-arrow {
    color: var(--gold);
    font-size: 12px;
    transition: transform 0.3s;
  }
  .card-body { padding: 14px 16px; }

  /* ─── STATUS BADGE ─── */
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 16px;
    border-radius: 50px;
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 14px;
  }
  .status-active {
    background: rgba(0,255,136,0.12);
    border: 1px solid rgba(0,255,136,0.4);
    color: var(--neon-green);
    box-shadow: 0 0 15px rgba(0,255,136,0.15);
  }
  .status-inactive {
    background: rgba(255,51,102,0.12);
    border: 1px solid rgba(255,51,102,0.4);
    color: var(--neon-red);
  }
  .blink { animation: blink 1.2s step-end infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

  /* ─── INFO ROWS ─── */
  .info-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .info-row:last-child { border-bottom: none; padding-bottom: 0; }
  .info-label {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 130px;
    font-size: 12px;
    color: var(--dim);
    font-weight: 600;
    letter-spacing: 0.5px;
    flex-shrink: 0;
  }
  .info-label span { font-size: 15px; }
  .info-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    word-break: break-all;
    flex: 1;
  }
  .info-value.highlight { color: var(--neon-blue); font-family: 'Orbitron', monospace; font-size: 11px; }
  .info-value.green { color: var(--neon-green); }
  .info-value.gold { color: var(--gold); }
  .info-value.password {
    font-family: monospace;
    background: rgba(0,207,255,0.07);
    padding: 2px 8px;
    border-radius: 5px;
    border: 1px solid rgba(0,207,255,0.2);
    cursor: pointer;
    transition: background 0.2s;
    position: relative;
  }
  .info-value.password:hover { background: rgba(0,207,255,0.15); }

  /* ─── CONNECTIONS BAR ─── */
  .conn-bar-wrap {
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }
  .conn-bar {
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    overflow: hidden;
  }
  .conn-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--neon-green), var(--neon-blue));
    border-radius: 10px;
    transition: width 1s ease;
  }
  .conn-text { font-size: 12px; font-weight: 700; color: var(--neon-green); }

  /* ─── DATES ─── */
  .dates-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .date-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    text-align: center;
  }
  .date-box-label {
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--dim);
    margin-bottom: 6px;
  }
  .date-box-value {
    font-family: 'Orbitron', monospace;
    font-size: 12px;
    font-weight: 700;
  }
  .date-box-value.created { color: var(--neon-blue); }
  .date-box-value.expires { color: var(--gold); }
  .days-left {
    font-size: 10px;
    color: var(--neon-green);
    margin-top: 4px;
  }

  /* ─── CONTENT STATS ─── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .stat-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 8px;
    text-align: center;
    transition: border-color 0.3s, transform 0.2s;
  }
  .stat-box:hover { border-color: rgba(255,215,0,0.5); transform: translateY(-2px); }
  .stat-icon { font-size: 20px; margin-bottom: 6px; }
  .stat-label { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--dim); margin-bottom: 4px; }
  .stat-value { font-family: 'Orbitron', monospace; font-size: 14px; font-weight: 900; color: var(--gold); }

  /* ─── LINKS ─── */
  .links-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .link-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 11px;
    border-radius: 10px;
    text-decoration: none;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
  }
  .link-m3u {
    background: linear-gradient(135deg, rgba(0,207,255,0.15), rgba(0,207,255,0.05));
    border: 1px solid rgba(0,207,255,0.4);
    color: var(--neon-blue);
  }
  .link-m3u:hover { background: rgba(0,207,255,0.25); box-shadow: 0 0 15px rgba(0,207,255,0.2); }
  .link-epg {
    background: linear-gradient(135deg, rgba(255,165,0,0.15), rgba(255,165,0,0.05));
    border: 1px solid rgba(255,165,0,0.4);
    color: var(--gold2);
  }
  .link-epg:hover { background: rgba(255,165,0,0.25); box-shadow: 0 0 15px rgba(255,165,0,0.2); }
  .link-copy {
    background: linear-gradient(135deg, rgba(0,255,136,0.12), rgba(0,255,136,0.04));
    border: 1px solid rgba(0,255,136,0.3);
    color: var(--neon-green);
  }
  .link-copy:hover { background: rgba(0,255,136,0.2); }

  /* ─── CATEGORIES ─── */
  .cat-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .cat-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
    border-left: 3px solid var(--gold2);
    transition: background 0.2s;
  }
  .cat-item:hover { background: rgba(255,255,255,0.06); }
  .cat-flag { font-size: 16px; margin-right: 8px; }
  .cat-name { font-size: 12px; font-weight: 600; flex: 1; }
  .cat-count {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    color: var(--gold);
    background: rgba(255,215,0,0.1);
    padding: 2px 8px;
    border-radius: 20px;
    border: 1px solid rgba(255,215,0,0.2);
  }
  .cat-more {
    text-align: center;
    padding: 10px;
    font-size: 12px;
    color: var(--dim);
    font-style: italic;
  }

  /* ─── VERIFIED FOOTER ─── */
  .verified-footer {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 0 0 14px 14px;
    padding: 14px 16px;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin-top: 10px;
  }
  .verified-footer::before {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--gold2), var(--neon-blue), var(--gold2));
    background-size: 200% 100%;
    animation: shimmer 2s linear infinite;
  }
  .verified-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 12px;
    color: var(--dim);
    margin: 3px 0;
  }
  .verified-row .check { color: var(--neon-green); font-size: 14px; }
  .verified-row strong { color: var(--text); }

  /* ─── BOT CONTROLS ─── */
  .bot-panel {
    background: var(--card2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 10px;
    position: relative;
    overflow: hidden;
  }
  .bot-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--neon-green), var(--neon-blue));
    background-size: 200% 100%;
    animation: shimmer 1.5s linear infinite;
  }
  .bot-title {
    font-family: 'Orbitron', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--neon-green);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .bot-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--neon-green);
    box-shadow: 0 0 8px var(--neon-green);
    animation: blink 1s ease-in-out infinite;
  }
  .bot-controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .bot-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 11px;
    border-radius: 10px;
    font-family: 'Orbitron', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
  }
  .btn-start {
    background: linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,255,136,0.08));
    border: 1px solid rgba(0,255,136,0.4);
    color: var(--neon-green);
  }
  .btn-start:hover { background: rgba(0,255,136,0.3); box-shadow: 0 0 15px rgba(0,255,136,0.2); transform: translateY(-1px); }
  .btn-stop {
    background: linear-gradient(135deg, rgba(255,51,102,0.2), rgba(255,51,102,0.08));
    border: 1px solid rgba(255,51,102,0.4);
    color: var(--neon-red);
  }
  .btn-stop:hover { background: rgba(255,51,102,0.3); box-shadow: 0 0 15px rgba(255,51,102,0.2); transform: translateY(-1px); }
  .btn-deploy {
    background: linear-gradient(135deg, rgba(0,207,255,0.2), rgba(0,207,255,0.08));
    border: 1px solid rgba(0,207,255,0.4);
    color: var(--neon-blue);
  }
  .btn-deploy:hover { background: rgba(0,207,255,0.3); transform: translateY(-1px); }
  .btn-github {
    background: linear-gradient(135deg, rgba(255,215,0,0.15), rgba(255,215,0,0.05));
    border: 1px solid rgba(255,215,0,0.4);
    color: var(--gold);
  }
  .btn-github:hover { background: rgba(255,215,0,0.2); transform: translateY(-1px); }
  .bot-status-bar {
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(0,255,136,0.05);
    border: 1px solid rgba(0,255,136,0.15);
    border-radius: 8px;
    font-size: 11px;
    color: var(--dim);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  #bot-status-text { color: var(--neon-green); font-weight: 600; }

  /* ─── TOAST ─── */
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: rgba(0,255,136,0.15);
    border: 1px solid rgba(0,255,136,0.4);
    color: var(--neon-green);
    padding: 10px 20px;
    border-radius: 50px;
    font-size: 12px;
    font-weight: 600;
    transition: transform 0.3s;
    z-index: 999;
    pointer-events: none;
  }
  .toast.show { transform: translateX(-50%) translateY(0); }

  /* ─── COLLAPSIBLE ─── */
  .collapsible { overflow: hidden; transition: max-height 0.4s ease; }
  .collapsed { max-height: 0 !important; }

  /* ─── COUNTRY FLAG COLORS ─── */
  .cat-item:nth-child(odd) { border-left-color: var(--gold2); }
  .cat-item:nth-child(even) { border-left-color: var(--neon-blue); }
</style>
</head>
<body>

<div class="wrapper">

  <!-- BOT CONTROLS -->
  <div class="bot-panel">
    <div class="bot-title">
      <div class="bot-dot"></div>
      PANEL DE CONTROL — BOT 24/7
    </div>
    <div class="bot-controls">
      <button class="bot-btn btn-start" onclick="botAction('start')">▶ INICIAR BOT</button>
      <button class="bot-btn btn-stop" onclick="botAction('stop')">⏹ DETENER BOT</button>
      <button class="bot-btn btn-deploy" onclick="openRender()">☁ RENDER DEPLOY</button>
      <button class="bot-btn btn-github" onclick="openGitHub()">⚡ GITHUB REPO</button>
    </div>
    <div class="bot-status-bar">
      <span>ESTADO:</span>
      <span id="bot-status-text">EN LÍNEA ✓</span>
      <span style="margin-left:auto;font-size:10px;" id="bot-uptime">Uptime: 00:00:00</span>
    </div>
  </div>

  <!-- HEADER -->
  <div class="header">
    <div class="scorpion-title">🦂 BY LUIS R 🦂</div>
    <div class="main-title">INFORMACIÓN DE LA CUENTA</div>
    <div class="scorpion-title" style="font-size:11px;letter-spacing:2px;color:var(--neon-blue);margin-top:4px;">★彡 ULTRA PRO EDITION 彡★</div>
  </div>

  <!-- DIVIDER -->
  <div class="divider"></div>

  <!-- ACCOUNT STATUS -->
  <div class="card">
    <div class="card-header" onclick="toggle('account')">
      <span class="card-header-icon">👤</span>
      <span class="card-header-title">★彡 CUENTA INFO 彡★</span>
      <span class="card-header-arrow" id="arrow-account">▼</span>
    </div>
    <div class="card-body collapsible" id="account" style="max-height:1000px;">
      <div style="margin-bottom:12px;">
        <div class="status-badge status-active">
          <span class="blink">🟢</span>
          CUENTA VÁLIDA — ACTIVA
        </div>
      </div>

      <div class="info-row">
        <div class="info-label"><span>⏲</span> Estado</div>
        <div class="info-value green">✅ ACTIVA</div>
      </div>
      <div class="info-row">
        <div class="info-label"><span>🧪</span> Trial</div>
        <div class="info-value">No Trial</div>
      </div>
      <div class="info-row">
        <div class="info-label"><span>🌐</span> Portal</div>
        <div class="info-value highlight" id="portal-val">tv.nstvlatino.com:8443</div>
      </div>
      <div class="info-row">
        <div class="info-label"><span>👤</span> Usuario</div>
        <div class="info-value highlight" id="user-val">diegovaldez2</div>
      </div>
      <div class="info-row">
        <div class="info-label"><span>🔑</span> Contraseña</div>
        <div class="info-value password" id="pass-val" onclick="copyField('pass-val','Contraseña copiada!')" title="Clic para copiar">092060702</div>
      </div>
      <div class="info-row">
        <div class="info-label"><span>📍</span> País</div>
        <div class="info-value">🇺🇸 United States</div>
      </div>
    </div>
  </div>

  <!-- DATES -->
  <div class="card">
    <div class="card-header" onclick="toggle('dates')">
      <span class="card-header-icon">📅</span>
      <span class="card-header-title">★彡 FECHAS 彡★</span>
      <span class="card-header-arrow" id="arrow-dates">▼</span>
    </div>
    <div class="card-body collapsible" id="dates" style="max-height:500px;">
      <div class="dates-grid">
        <div class="date-box">
          <div class="date-box-label">📆 Fecha Creación</div>
          <div class="date-box-value created" id="created-date">—</div>
          <div class="days-left" id="days-since">calculando...</div>
        </div>
        <div class="date-box">
          <div class="date-box-label">⏲ Vencimiento</div>
          <div class="date-box-value expires">09/06/2026</div>
          <div class="days-left" id="days-left-val">calculando...</div>
        </div>
      </div>
      <div style="margin-top:12px;" class="info-row">
        <div class="info-label"><span>👁</span> Conexiones</div>
        <div class="conn-bar-wrap">
          <div class="conn-bar"><div class="conn-fill" id="conn-fill" style="width:33%"></div></div>
          <span class="conn-text">1 / 3</span>
        </div>
      </div>
    </div>
  </div>

  <!-- CONTENT STATS -->
  <div class="card">
    <div class="card-header" onclick="toggle('content')">
      <span class="card-header-icon">📺</span>
      <span class="card-header-title">★彡 CONTENIDO 彡★</span>
      <span class="card-header-arrow" id="arrow-content">▼</span>
    </div>
    <div class="card-body collapsible" id="content" style="max-height:500px;">
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-icon">📺</div>
          <div class="stat-label">En Vivo</div>
          <div class="stat-value" id="live-count">?</div>
        </div>
        <div class="stat-box">
          <div class="stat-icon">🎥</div>
          <div class="stat-label">VOD</div>
          <div class="stat-value" id="vod-count">?</div>
        </div>
        <div class="stat-box">
          <div class="stat-icon">📹</div>
          <div class="stat-label">Series</div>
          <div class="stat-value" id="series-count">?</div>
        </div>
      </div>
    </div>
  </div>

  <!-- LINKS -->
  <div class="card">
    <div class="card-header" onclick="toggle('links')">
      <span class="card-header-icon">🔗</span>
      <span class="card-header-title">★彡 ENLACES 彡★</span>
      <span class="card-header-arrow" id="arrow-links">▼</span>
    </div>
    <div class="card-body collapsible" id="links" style="max-height:500px;">
      <div class="links-grid">
        <a class="link-btn link-m3u" href="https://tv.nstvlatino.com:8443/get.php?username=diegovaldez2&password=092060702&type=m3u_plus" target="_blank">
          📡 M3U Link
        </a>
        <a class="link-btn link-epg" href="https://tv.nstvlatino.com:8443/xmltv.php?username=diegovaldez2&password=092060702" target="_blank">
          📋 EPG Link
        </a>
        <button class="link-btn link-copy" onclick="copyM3U()">📋 Copiar M3U</button>
        <button class="link-btn link-copy" onclick="copyEPG()">📋 Copiar EPG</button>
      </div>
    </div>
  </div>

  <!-- CATEGORIES -->
  <div class="card">
    <div class="card-header" onclick="toggle('cats')">
      <span class="card-header-icon">📂</span>
      <span class="card-header-title">★彡 CATEGORÍAS 彡★</span>
      <span class="card-header-arrow" id="arrow-cats">▼</span>
    </div>
    <div class="card-body collapsible" id="cats" style="max-height:2000px;">
      <div class="cat-list">
        <div class="cat-item"><span class="cat-flag">🎬</span><span class="cat-name">CINE</span><span class="cat-count">101</span></div>
        <div class="cat-item"><span class="cat-flag">🌍</span><span class="cat-name">MUNDO Y CULTURA</span><span class="cat-count">28</span></div>
        <div class="cat-item"><span class="cat-flag">⚽</span><span class="cat-name">LATINO DEPORTES</span><span class="cat-count">77</span></div>
        <div class="cat-item"><span class="cat-flag">🎭</span><span class="cat-name">ENTRETENIMIENTO</span><span class="cat-count">23</span></div>
        <div class="cat-item"><span class="cat-flag">🧒</span><span class="cat-name">INFANTILES</span><span class="cat-count">20</span></div>
        <div class="cat-item"><span class="cat-flag">🏠</span><span class="cat-name">EL GRAN HERMANO</span><span class="cat-count">7</span></div>
        <div class="cat-item"><span class="cat-flag">🎪</span><span class="cat-name">EVENTOS ESPECIALES & DISNEY+</span><span class="cat-count">401</span></div>
        <div class="cat-item"><span class="cat-flag">🏈</span><span class="cat-name">FUTBOL AMERICANO NFL</span><span class="cat-count">8</span></div>
        <div class="cat-item"><span class="cat-flag">🎞</span><span class="cat-name">CINEMA PREMIUM</span><span class="cat-count">15</span></div>
        <!-- PAÍSES -->
        <div style="height:8px;"></div>
        <div class="cat-item" style="border-left-color:#00bfff;"><span class="cat-flag">🇺🇾</span><span class="cat-name">URUGUAY</span><span class="cat-count">41</span></div>
        <div class="cat-item" style="border-left-color:#006847;"><span class="cat-flag">🇲🇽</span><span class="cat-name">MÉXICO</span><span class="cat-count">45</span></div>
        <div class="cat-item" style="border-left-color:#d52b1e;"><span class="cat-flag">🇨🇱</span><span class="cat-name">CHILE</span><span class="cat-count">43</span></div>
        <div class="cat-item" style="border-left-color:#FFD100;"><span class="cat-flag">🇪🇨</span><span class="cat-name">ECUADOR</span><span class="cat-count">23</span></div>
        <div class="cat-item" style="border-left-color:#74ACDF;"><span class="cat-flag">🇦🇷</span><span class="cat-name">ARGENTINA</span><span class="cat-count">49</span></div>
        <div class="cat-item" style="border-left-color:#FCD116;"><span class="cat-flag">🇨🇴</span><span class="cat-name">COLOMBIA</span><span class="cat-count">21</span></div>
        <div class="cat-item" style="border-left-color:#CF142B;"><span class="cat-flag">🇵🇪</span><span class="cat-name">PERÚ</span><span class="cat-count">18</span></div>
        <div class="cat-item" style="border-left-color:#00247D;"><span class="cat-flag">🇻🇪</span><span class="cat-name">VENEZUELA</span><span class="cat-count">22</span></div>
        <div class="cat-item" style="border-left-color:#009B77;"><span class="cat-flag">🇧🇴</span><span class="cat-name">BOLIVIA</span><span class="cat-count">12</span></div>
        <div class="cat-item" style="border-left-color:#002395;"><span class="cat-flag">🇵🇦</span><span class="cat-name">PANAMÁ</span><span class="cat-count">9</span></div>
        <div class="cat-item" style="border-left-color:#CE1126;"><span class="cat-flag">🇩🇴</span><span class="cat-name">REP. DOMINICANA</span><span class="cat-count">14</span></div>
        <div class="cat-item" style="border-left-color:#003087;"><span class="cat-flag">🇺🇸</span><span class="cat-name">ESTADOS UNIDOS</span><span class="cat-count">38</span></div>
        <div class="cat-item" style="border-left-color:#003366;"><span class="cat-flag">🇪🇸</span><span class="cat-name">ESPAÑA</span><span class="cat-count">31</span></div>
        <div class="cat-more">➕ ...y 12 categorías más disponibles</div>
      </div>
    </div>
  </div>

  <!-- VERIFIED FOOTER -->
  <div class="verified-footer">
    <div class="verified-row">
      <span class="check">✔️</span>
      Verificado para <strong id="tg-user">@usuario_telegram</strong>
    </div>
    <div class="verified-row">
      <span>🕐</span>
      <strong id="current-date-footer">—</strong>
    </div>
    <div style="margin-top:10px;" class="scorpion-title">🦂 BY LUIS R 🦂</div>
  </div>

</div>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<script>
// ─── DATES ───
const now = new Date();
const created = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30);
const expires = new Date('2026-06-09T05:00:00');

function pad(n){ return String(n).padStart(2,'0'); }
function fmt(d){ return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}`; }

document.getElementById('created-date').textContent = fmt(created);
const sinDays = Math.floor((now - created)/(1000*60*60*24));
document.getElementById('days-since').textContent = `Hace ${sinDays} días`;
const daysLeft = Math.max(0, Math.ceil((expires - now)/(1000*60*60*24)));
document.getElementById('days-left-val').textContent = `${daysLeft} días restantes`;

// Footer date
const months = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
document.getElementById('current-date-footer').textContent =
  `${now.getDate()} de ${months[now.getMonth()]} de ${now.getFullYear()} — ${pad(now.getHours())}:${pad(now.getMinutes())}`;

// ─── COLLAPSIBLE ───
function toggle(id){
  const el = document.getElementById(id);
  const arrow = document.getElementById('arrow-' + id);
  if(!el) return;
  if(el.classList.contains('collapsed')){
    el.classList.remove('collapsed');
    if(arrow) arrow.textContent = '▼';
  } else {
    el.classList.add('collapsed');
    if(arrow) arrow.textContent = '▶';
  }
}

// ─── COPY ───
function showToast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 2000);
}
function copyField(id, msg){
  const val = document.getElementById(id).textContent;
  navigator.clipboard.writeText(val).then(()=>showToast('✓ '+msg)).catch(()=>showToast('✓ Copiado'));
}
function copyM3U(){
  const url = 'https://tv.nstvlatino.com:8443/get.php?username=diegovaldez2&password=092060702&type=m3u_plus';
  navigator.clipboard.writeText(url).then(()=>showToast('✓ M3U copiado!')).catch(()=>{});
}
function copyEPG(){
  const url = 'https://tv.nstvlatino.com:8443/xmltv.php?username=diegovaldez2&password=092060702';
  navigator.clipboard.writeText(url).then(()=>showToast('✓ EPG copiado!')).catch(()=>{});
}

// ─── BOT CONTROLS ───
let botRunning = true;
let startTime = Date.now();
let uptimeInterval;

function updateUptime(){
  if(!botRunning){ return; }
  const diff = Math.floor((Date.now()-startTime)/1000);
  const h = Math.floor(diff/3600), m = Math.floor((diff%3600)/60), s = diff%60;
  document.getElementById('bot-uptime').textContent =
    `Uptime: ${pad(h)}:${pad(m)}:${pad(s)}`;
}
uptimeInterval = setInterval(updateUptime, 1000);

function botAction(action){
  const statusEl = document.getElementById('bot-status-text');
  if(action==='start'){
    botRunning = true;
    startTime = Date.now();
    clearInterval(uptimeInterval);
    uptimeInterval = setInterval(updateUptime, 1000);
    statusEl.style.color = 'var(--neon-green)';
    statusEl.textContent = 'EN LÍNEA ✓';
    showToast('🟢 Bot iniciado exitosamente');
  } else {
    botRunning = false;
    clearInterval(uptimeInterval);
    document.getElementById('bot-uptime').textContent = 'Uptime: --:--:--';
    statusEl.style.color = 'var(--neon-red)';
    statusEl.textContent = 'DETENIDO ✗';
    showToast('🔴 Bot detenido');
  }
}

function openRender(){
  window.open('https://render.com/deploy','_blank');
  showToast('☁ Abriendo Render...');
}
function openGitHub(){
  window.open('https://github.com','_blank');
  showToast('⚡ Abriendo GitHub...');
}

// ─── FETCH CONTENT COUNTS (simulado) ───
setTimeout(()=>{
  document.getElementById('live-count').textContent = '5,240';
  document.getElementById('vod-count').textContent = '12,880';
  document.getElementById('series-count').textContent = '3,450';
}, 1200);
</script>
</body>
</html>
