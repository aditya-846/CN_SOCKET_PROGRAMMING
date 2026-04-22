# 🌐 CN Socket Programming

## 📌 Overview
This repository contains implementations of **socket programming in C**, demonstrating communication between systems using **TCP/UDP protocols**.

It is designed to help understand **client-server architecture** and core **computer networking concepts**.

---

## 🎯 Objectives
- Learn how socket programming works
- Understand client-server communication
- Implement TCP and UDP protocols
- Build basic networking applications

---

## 🛠️ Technologies Used
- **Language:** C
- **Concepts:** Socket Programming, Networking
- **Protocols:** TCP / UDP

---

## 📂 Project Structure
CN_SOCKET_PROGRAMMING/
│
├── server.c # TCP Server
├── client.c # TCP Client
├── udp_server.c # UDP Server (if included)
├── udp_client.c # UDP Client (if included)
├── README.md # Documentation


---

## ⚙️ How It Works
Socket programming allows two systems to communicate over a network.

### 🔹 Server Side
1. Create socket
2. Bind socket to IP and port
3. Listen for connections
4. Accept client connection
5. Send/Receive data

### 🔹 Client Side
1. Create socket
2. Connect to server
3. Send/Receive data

---

## ▶️ How to Run

### 🔹 Compile
```bash
gcc server.c -o server
gcc client.c -o client

./server

./client
```
Server: Waiting for connection...
Client: Connected to server
Client: Hello Server!
Server: Hello Client!

💡 Key Concepts Covered
socket()
bind()
listen()
accept()
connect()
send() and recv()

🚀 Applications
Chat applications
File transfer systems
Web communication
Distributed systems

📄 License
This project is for educational purposes and is free to use.
