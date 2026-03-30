<div align="center">

# 👋 Hi, I'm Nattacha Ackahat

### Network Engineering Student · KKU · CCNA Certified Track

[![Email](https://img.shields.io/badge/Email-nattacha.a%40kkumail.com-blue?style=flat-square&logo=gmail&logoColor=white)](mailto:nattacha.a@kkumail.com)
[![GitHub](https://img.shields.io/badge/GitHub-bbthecat-181717?style=flat-square&logo=github)](https://github.com/bbthecat)
[![Cisco](https://img.shields.io/badge/Cisco-CCNA%20Track-1BA0D7?style=flat-square&logo=cisco&logoColor=white)](https://www.netacad.com/)

</div>

---

## 🎯 About Me

> Computer Science / Network Engineering student at **Khon Kaen University (KKU)**  
> Passionate about **network architecture**, **microservices**, and **cloud-native infrastructure**.  
> Building real-world lab environments with Docker to simulate enterprise network topologies.

---

## 📊 Academic Results — CCNA: Introduction to Networks

<div align="center">

| Category | Score | Grade |
|:--------:|:-----:|:-----:|
| 🏆 **Final Exam** | **100 / 100** | **100%** |
| 📝 Module Group Exams | 579 / 600 | 96.5% |
| 🌐 Overall Class Grade | — | **68.6%** |

</div>

### 📋 Checkpoint Exam Breakdown

| # | Exam | Date | Score |
|---|------|------|:-----:|
| 1 | Checkpoint: Basic Network Connectivity and Communications | 10 Jan 2026 | ⭐ **94/100** |
| 2 | Checkpoint: Ethernet Concepts | 16 Jan 2026 | 🏅 **100/100** |
| 3 | Checkpoint: Communicating Between Networks | 23 Jan 2026 | 🏅 **100/100** |
| 4 | Checkpoint: IP Addressing | 20 Feb 2026 | ⭐ **94/100** |
| 5 | Checkpoint: Network Application Communications | 20 Feb 2026 | ⭐ **97/100** |
| 6 | Checkpoint: Building and Securing a Small Network | 20 Feb 2026 | ⭐ **94/100** |
| 🎓 | **CCNA: Introduction to Networks — Final Exam** | 27 Mar 2026 | 🥇 **100/100** |

---

## 🚀 Featured Project — Lab 7

### Network & Microservices Lab
> Docker-based enterprise network simulation replacing Cisco Packet Tracer

[![Repo](https://img.shields.io/badge/Repo-Network--Microservices-181717?style=flat-square&logo=github)](https://github.com/bbthecat/Network-Microservices)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://github.com/bbthecat/Network-Microservices)
[![Nginx](https://img.shields.io/badge/Nginx-Gateway-009639?style=flat-square&logo=nginx)](https://github.com/bbthecat/Network-Microservices)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)](https://github.com/bbthecat/Network-Microservices)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis)](https://github.com/bbthecat/Network-Microservices)

```
HOST (port 80/8000)
        │
        ▼
┌──────────────────┐  172.20.0.0/24 (frontend-dmz)
│   Nginx Gateway  │  Rate Limit · ACL · Load Balancer
└────────┬─────────┘
═════════╪═══ FIREWALL ════════════════
         │
┌────────┴──────────────────────────────┐  172.21.0.0/24 (backend-secure)
│  api-1 ──┐                           │
│           ├─ PostgreSQL · Redis       │
│  api-2 ──┘                           │
│  Loki · Promtail · Grafana           │
└───────────────────────────────────────┘
```

**Resiliency Test Results: 24/24 PASS ✅**

| Test | Result |
|------|:------:|
| All containers healthy | ✅ |
| Load balancer distributes traffic | ✅ |
| Zero-downtime failover | ✅ |
| Rate limiting (429 on burst) | ✅ |
| Redis cache 83% faster than DB | ✅ |
| Cluster recovery after restart | ✅ |

---

## 📚 All Assignments

> 📎 **[View All Assignments PDF](https://drive.google.com/file/d/1j078RIAKxEhTDKiFeY7rLxs90CA9mNj3/view?usp=sharing)**

| Lab | Topic | Repo / Report |
|-----|-------|:-------------:|
| Lab 6 | Network Security & ACL Configuration | [📄 LAB_REPORT.md](https://github.com/bbthecat/Network-Microservices/blob/main/LAB_REPORT.md) |
| Lab 7 | Docker-based Microservices Topology | [📦 Network-Microservices](https://github.com/bbthecat/Network-Microservices) |

---

## 🛠️ Tech Stack

<div align="center">

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=node.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Cisco](https://img.shields.io/badge/Cisco_CCNA-1BA0D7?style=for-the-badge&logo=cisco&logoColor=white)

</div>

---

## 📈 Skills

```
Network Architecture    ████████████████████  95%
Docker / Containers     ██████████████████░░  90%
Linux / Bash            ████████████████░░░░  80%
Security (ACL/Firewall) █████████████████░░░  85%
Python Scripting        ████████████████░░░░  80%
Observability (Loki)    ██████████████░░░░░░  70%
```

---

<div align="center">

*CCNA: Introduction to Networks — Final Exam Score: **100/100** 🎓*

</div>
