PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	is_active_user BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, is_superadmin BOOLEAN NOT NULL DEFAULT 0, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);
INSERT INTO users VALUES(1,'admin','admin@erp.local','scrypt:32768:8:1$QyNE66QARkeKxWTW$17c5524a73dc7c921e6f786fb81ea285d454f157fc025b46399a839a5d604f9c2035bc678e73688fa35376ba0bf13bf7b25762a67dcc6500a8eae97fc4c02c1c','Super Admin',1,'2026-04-03 18:23:22.738539','2026-04-03 18:23:22.738543',1);
INSERT INTO users VALUES(3,'laura.bianchi','laura@erp.local','scrypt:32768:8:1$kh4rzYBICiTb99G2$413b7c060c8538ffc65ac9edf91df58711cb3279924af179117f89bc8fe92559b280997e2a3ae7c853d6b8ce57eba246e6712ace6fdc9128b58e42f675abf178','Laura Bianchi',1,'2026-04-03 18:23:23.033513','2026-04-03 18:23:23.033514',0);
CREATE TABLE agents (
	id INTEGER NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	last_name VARCHAR(100) NOT NULL, 
	email VARCHAR(120), 
	default_percentage NUMERIC(5, 2), 
	is_active BOOLEAN, 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO agents VALUES(1,'Marco','Verdi','marco.verdi@mail.it',10,1,'Agente senior','2026-04-03 18:23:23.034315','2026-04-03 18:23:23.034317');
INSERT INTO agents VALUES(2,'Anna','Neri','anna.neri@mail.it',8,1,'Agente area Nord','2026-04-03 18:23:23.034317','2026-04-03 18:23:23.034318');
INSERT INTO agents VALUES(3,'Luca','Gialli','luca.gialli@mail.it',12,1,'Agente area Sud','2026-04-03 18:23:23.034318','2026-04-03 18:23:23.034318');
INSERT INTO agents VALUES(4,'Browser Test Agent','',NULL,15,1,'','2026-04-04 08:24:15.686928','2026-04-04 08:24:15.686929');
INSERT INTO agents VALUES(5,'Browser Test Agent','',NULL,15,1,'','2026-04-04 08:45:02.876745','2026-04-04 08:45:02.876746');
CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	username VARCHAR(80) NOT NULL, 
	timestamp DATETIME NOT NULL, 
	action_type VARCHAR(50) NOT NULL, 
	entity_type VARCHAR(50), 
	entity_id INTEGER, 
	description TEXT NOT NULL, 
	old_values TEXT, 
	new_values TEXT, 
	ip_address VARCHAR(45), 
	PRIMARY KEY (id)
);
INSERT INTO audit_logs VALUES(1,1,'admin','2026-04-01 09:00:00.000000','login','User',NULL,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(2,1,'admin','2026-04-01 09:05:00.000000','create','Agent',1,'Creato agente: Marco Verdi',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(3,1,'admin','2026-04-01 09:10:00.000000','create','RevenueActivity',NULL,'Creata attività: Progetto Sito Web Aziendale',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(4,1,'admin','2026-04-03 18:24:11.680661','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(5,1,'admin','2026-04-03 18:25:10.229813','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(6,1,'admin','2026-04-03 21:52:20.946026','logout','User',1,'Logout utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(7,1,'admin','2026-04-03 21:52:26.498006','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(8,1,'admin','2026-04-04 08:07:53.304362','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(9,1,'admin','2026-04-04 08:07:53.353943','create','RevenueActivity',6,'Creata attività: Browser Test Activity',NULL,'{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(10,1,'admin','2026-04-04 08:07:53.390713','status_change','RevenueActivity',6,'Modificata attività: Browser Test Edited','{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(11,1,'admin','2026-04-04 08:07:53.403979','create','ActivityCost',16,'Aggiunto costo "Browser Test Cost" all''attività "Browser Test Edited"',NULL,'{"category": "consulenza", "description": "Browser Test Cost", "amount": "250.50", "date": "2026-04-04", "cost_type": "operativo", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(12,1,'admin','2026-04-04 08:07:53.421067','create','ActivityParticipant',14,'Aggiunto partecipante "Browser Test Participant" all''attività "Browser Test Edited"',NULL,'{"participant_name": "Browser Test Participant", "role_description": "Tester", "work_share": "60.00", "fixed_compensation": "100.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(13,1,'admin','2026-04-04 08:07:53.514810','user_create','User',4,'Creato utente: browseruser',NULL,'{"username": "browseruser", "is_active_user": true}','127.0.0.1');
INSERT INTO audit_logs VALUES(14,1,'admin','2026-04-04 08:07:53.535541','delete','User',4,'Eliminato utente: browseruser','{"username": "browseruser", "is_active_user": true}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(15,1,'admin','2026-04-04 08:07:53.655322','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(16,1,'admin','2026-04-04 08:07:53.704694','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(17,1,'admin','2026-04-04 08:07:53.716542','create','RevenueActivity',7,'Creata attività: <script>alert(1)</script>',NULL,'{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(18,1,'admin','2026-04-04 08:07:53.767880','user_create','User',4,'Creato utente: test_operator',NULL,'{"username": "test_operator", "is_active_user": true}','127.0.0.1');
INSERT INTO audit_logs VALUES(19,4,'test_operator','2026-04-04 08:07:53.816750','login','User',4,'Login utente: test_operator',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(20,4,'test_operator','2026-04-04 08:07:53.830820','create','RevenueActivity',8,'Creata attività: Operator Activity',NULL,'{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(21,1,'admin','2026-04-04 08:07:53.842585','delete','RevenueActivity',6,'Eliminata attività: Browser Test Edited','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(22,1,'admin','2026-04-04 08:07:53.852072','logout','User',1,'Logout utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(23,1,'admin','2026-04-04 08:08:18.170811','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(24,1,'admin','2026-04-04 08:11:43.079714','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(25,1,'admin','2026-04-04 08:24:15.571132','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(26,1,'admin','2026-04-04 08:24:15.613691','create','RevenueActivity',9,'Creata attività: Browser Test Activity',NULL,'{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(27,1,'admin','2026-04-04 08:24:15.646754','status_change','RevenueActivity',9,'Modificata attività: Browser Test Edited','{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(28,1,'admin','2026-04-04 08:24:15.658093','create','ActivityCost',16,'Aggiunto costo "Browser Test Cost" all''attività "Browser Test Edited"',NULL,'{"category": "consulenza", "description": "Browser Test Cost", "amount": "250.50", "date": "2026-04-04", "cost_type": "operativo", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(29,1,'admin','2026-04-04 08:24:15.672516','create','ActivityParticipant',14,'Aggiunto partecipante "Browser Test Participant" all''attività "Browser Test Edited"',NULL,'{"participant_name": "Browser Test Participant", "role_description": "Tester", "work_share": "60.00", "fixed_compensation": "100.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(30,1,'admin','2026-04-04 08:24:15.687974','create','Agent',4,'Creato agente: Browser Test Agent',NULL,'{"first_name": "Browser Test Agent", "last_name": "", "email": null, "default_percentage": "15.00", "is_active": true, "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(31,1,'admin','2026-04-04 08:24:15.755021','user_create','User',5,'Creato utente: browseruser',NULL,'{"username": "browseruser", "is_active_user": true}','127.0.0.1');
INSERT INTO audit_logs VALUES(32,1,'admin','2026-04-04 08:24:15.775812','delete','User',5,'Eliminato utente: browseruser','{"username": "browseruser", "is_active_user": true}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(33,1,'admin','2026-04-04 08:24:15.899733','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(34,1,'admin','2026-04-04 08:24:15.948532','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(35,1,'admin','2026-04-04 08:24:15.961130','create','RevenueActivity',10,'Creata attività: <script>alert(1)</script>',NULL,'{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(36,4,'test_operator','2026-04-04 08:24:16.014062','login','User',4,'Login utente: test_operator',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(37,4,'test_operator','2026-04-04 08:24:16.028895','create','RevenueActivity',11,'Creata attività: Operator Activity',NULL,'{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(38,1,'admin','2026-04-04 08:24:16.040478','delete','RevenueActivity',9,'Eliminata attività: Browser Test Edited','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(39,1,'admin','2026-04-04 08:24:16.050591','logout','User',1,'Logout utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(40,1,'admin','2026-04-04 08:45:02.744894','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(41,1,'admin','2026-04-04 08:45:02.798251','create','RevenueActivity',12,'Creata attività: Browser Test Activity',NULL,'{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(42,1,'admin','2026-04-04 08:45:02.831331','status_change','RevenueActivity',12,'Modificata attività: Browser Test Edited','{"title": "Browser Test Activity", "description": "Created via browser test", "date": "2026-04-04", "status": "bozza", "total_revenue": "5000.00", "agent_id": null, "agent_percentage": "10.00", "notes": ""}','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(43,1,'admin','2026-04-04 08:45:02.843972','create','ActivityCost',16,'Aggiunto costo "Browser Test Cost" all''attività "Browser Test Edited"',NULL,'{"category": "consulenza", "description": "Browser Test Cost", "amount": "250.50", "date": "2026-04-04", "cost_type": "operativo", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(44,1,'admin','2026-04-04 08:45:02.859466','create','ActivityParticipant',14,'Aggiunto partecipante "Browser Test Participant" all''attività "Browser Test Edited"',NULL,'{"participant_name": "Browser Test Participant", "role_description": "Tester", "work_share": "60.00", "fixed_compensation": "100.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(45,1,'admin','2026-04-04 08:45:02.877567','create','Agent',5,'Creato agente: Browser Test Agent',NULL,'{"first_name": "Browser Test Agent", "last_name": "", "email": null, "default_percentage": "15.00", "is_active": true, "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(46,1,'admin','2026-04-04 08:45:02.946779','user_create','User',5,'Creato utente: browseruser',NULL,'{"username": "browseruser", "is_active_user": true}','127.0.0.1');
INSERT INTO audit_logs VALUES(47,1,'admin','2026-04-04 08:45:02.967762','delete','User',5,'Eliminato utente: browseruser','{"username": "browseruser", "is_active_user": true}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(48,1,'admin','2026-04-04 08:45:03.112283','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(49,1,'admin','2026-04-04 08:45:03.162292','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(50,1,'admin','2026-04-04 08:45:03.176912','create','RevenueActivity',13,'Creata attività: <script>alert(1)</script>',NULL,'{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(51,4,'test_operator','2026-04-04 08:45:03.235540','login','User',4,'Login utente: test_operator',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(52,4,'test_operator','2026-04-04 08:45:03.255364','create','RevenueActivity',14,'Creata attività: Operator Activity',NULL,'{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}','127.0.0.1');
INSERT INTO audit_logs VALUES(53,1,'admin','2026-04-04 08:45:03.270307','delete','RevenueActivity',12,'Eliminata attività: Browser Test Edited','{"title": "Browser Test Edited", "description": "", "date": "2026-04-04", "status": "confermata", "total_revenue": "7000.00", "agent_id": null, "agent_percentage": "12.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(54,1,'admin','2026-04-04 08:45:03.284282','logout','User',1,'Logout utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(55,1,'admin','2026-04-04 08:47:13.539871','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(56,1,'admin','2026-04-04 08:47:33.291139','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(57,1,'admin','2026-04-04 08:47:40.813506','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(58,1,'admin','2026-04-04 08:48:26.446666','login','User',1,'Login utente: admin',NULL,NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(59,1,'admin','2026-04-04 09:14:23.513765','delete','RevenueActivity',3,'Eliminata attività (bulk): Consulenza Strategica PMI','{"title": "Consulenza Strategica PMI", "description": "Analisi e piano strategico triennale", "date": "2026-04-15", "status": "chiusa", "total_revenue": "25000.00", "agent_id": "3", "agent_percentage": "12.00", "notes": null}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(60,1,'admin','2026-04-04 09:14:23.531077','delete','RevenueActivity',2,'Eliminata attività (bulk): Campagna Marketing Digitale','{"title": "Campagna Marketing Digitale", "description": "Gestione campagna social media per catena di ristoranti", "date": "2026-04-10", "status": "confermata", "total_revenue": "8000.00", "agent_id": "2", "agent_percentage": "8.00", "notes": null}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(61,1,'admin','2026-04-04 09:14:23.535510','delete','RevenueActivity',1,'Eliminata attività (bulk): Progetto Sito Web Aziendale','{"title": "Progetto Sito Web Aziendale", "description": "Realizzazione sito web corporate per azienda metalmeccanica", "date": "2026-04-05", "status": "confermata", "total_revenue": "15000.00", "agent_id": "1", "agent_percentage": "10.00", "notes": null}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(62,1,'admin','2026-04-04 09:14:23.539700','delete','RevenueActivity',7,'Eliminata attività (bulk): <script>alert(1)</script>','{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(63,1,'admin','2026-04-04 09:14:23.542876','delete','RevenueActivity',8,'Eliminata attività (bulk): Operator Activity','{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(64,1,'admin','2026-04-04 09:14:23.545823','delete','RevenueActivity',10,'Eliminata attività (bulk): <script>alert(1)</script>','{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(65,1,'admin','2026-04-04 09:14:23.548232','delete','RevenueActivity',11,'Eliminata attività (bulk): Operator Activity','{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(66,1,'admin','2026-04-04 09:14:23.550277','delete','RevenueActivity',13,'Eliminata attività (bulk): <script>alert(1)</script>','{"title": "<script>alert(1)</script>", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "100.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(67,1,'admin','2026-04-04 09:14:23.553333','delete','RevenueActivity',14,'Eliminata attività (bulk): Operator Activity','{"title": "Operator Activity", "description": "", "date": "2026-04-04", "status": "bozza", "total_revenue": "300.00", "agent_id": null, "agent_percentage": "0.00", "notes": ""}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(68,1,'admin','2026-04-04 09:14:23.555696','delete','RevenueActivity',4,'Eliminata attività (bulk): App Mobile E-commerce','{"title": "App Mobile E-commerce", "description": "Sviluppo app iOS e Android per negozio online", "date": "2026-04-02", "status": "bozza", "total_revenue": "35000.00", "agent_id": "1", "agent_percentage": "10.00", "notes": null}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(69,1,'admin','2026-04-04 09:14:39.398382','status_change','RevenueActivity',5,'Modificata attività: Formazione Aziendale IT','{"title": "Formazione Aziendale IT", "description": "Corso di formazione su cybersecurity per 30 dipendenti", "date": "2026-04-20", "status": "confermata", "total_revenue": "6000.00", "agent_id": "2", "agent_percentage": "8.00", "notes": null}','{"title": "Formazione Aziendale IT", "description": "Corso di formazione su cybersecurity per 30 dipendenti", "date": "2026-04-20", "status": "chiusa", "total_revenue": "6000.00", "agent_id": "2", "agent_percentage": "8.00", "notes": "None"}','127.0.0.1');
INSERT INTO audit_logs VALUES(70,1,'admin','2026-04-04 09:20:07.429782','delete','User',4,'Eliminato utente: test_operator','{"username": "test_operator", "is_active_user": true}',NULL,'127.0.0.1');
INSERT INTO audit_logs VALUES(71,1,'admin','2026-04-04 09:26:19.850478','delete','User',2,'Eliminato utente: mario.rossi','{"username": "mario.rossi", "is_active_user": true}',NULL,'127.0.0.1');
CREATE TABLE revenue_activities (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	date DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	total_revenue NUMERIC(12, 2) NOT NULL, 
	agent_id INTEGER, 
	agent_percentage NUMERIC(5, 2), 
	notes TEXT, 
	created_by INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
INSERT INTO revenue_activities VALUES(5,'Formazione Aziendale IT','Corso di formazione su cybersecurity per 30 dipendenti','2026-04-20','chiusa',6000,2,8,'None',1,'2026-04-03 18:23:23.037927','2026-04-04 09:14:39.394978');
CREATE TABLE activity_costs (
	id INTEGER NOT NULL, 
	activity_id INTEGER NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	date DATE NOT NULL, 
	cost_type VARCHAR(20) NOT NULL, 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(activity_id) REFERENCES revenue_activities (id)
);
INSERT INTO activity_costs VALUES(13,5,'materiale','Materiale didattico',400,'2026-04-20','operativo',NULL,'2026-04-03 18:23:23.038457');
INSERT INTO activity_costs VALUES(14,5,'trasporto','Trasferta formatore',250,'2026-04-20','operativo',NULL,'2026-04-03 18:23:23.038458');
INSERT INTO activity_costs VALUES(15,5,'spese_vive','Coffee break',150,'2026-04-20','extra',NULL,'2026-04-03 18:23:23.038458');
CREATE TABLE activity_participants (
	id INTEGER NOT NULL, 
	activity_id INTEGER NOT NULL, 
	participant_name VARCHAR(200) NOT NULL, 
	user_id INTEGER, 
	role_description VARCHAR(200), 
	work_share NUMERIC(5, 2) NOT NULL, 
	fixed_compensation NUMERIC(12, 2), 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(activity_id) REFERENCES revenue_activities (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
INSERT INTO activity_participants VALUES(13,5,'Laura Bianchi',3,'Coordinamento',30,0,NULL,'2026-04-03 18:23:23.038543');
COMMIT;
