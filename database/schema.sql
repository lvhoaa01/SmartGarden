-- ============================================================
-- SmartGarden — Schema v2.0 (SQL Server)
-- 3 bảng: Nodes, Telemetry, Action_Logs
-- Nguyên tắc: KHÔNG lưu ảnh Base64 vào DB.
-- ============================================================

USE master;
GO
IF EXISTS (SELECT name FROM sys.databases WHERE name = N'SmartGarden')
BEGIN
    ALTER DATABASE SmartGarden SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE SmartGarden;
END
GO
CREATE DATABASE SmartGarden;
GO
USE SmartGarden;
GO

-- ===================== 1. NODES =====================
CREATE TABLE Nodes (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(100)   NOT NULL,
    location    NVARCHAR(200)   NULL,
    status      VARCHAR(20)     NOT NULL DEFAULT 'offline',
    last_seen   DATETIME2       NULL
);
GO

INSERT INTO Nodes (name, location, status)
VALUES (N'Node Test 01', N'Bàn thí nghiệm', 'offline');
GO

-- ===================== 2. TELEMETRY =====================
CREATE TABLE Telemetry (
    id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    node_id     INT             NOT NULL,
    temperature FLOAT           NOT NULL,
    humidity    FLOAT           NOT NULL,
    avg_soil    FLOAT           NOT NULL,
    light_lux   FLOAT           NOT NULL,
    image_path  NVARCHAR(500)   NULL,
    created_at  DATETIME2       NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Telemetry_Node FOREIGN KEY (node_id) REFERENCES Nodes(id)
);
GO

CREATE INDEX IX_Telemetry_NodeId_CreatedAt
    ON Telemetry (node_id, created_at DESC);
GO

-- ===================== 3. ACTION_LOGS =====================
CREATE TABLE Action_Logs (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    node_id         INT             NOT NULL,
    telemetry_id    BIGINT          NULL,
    action_type     INT             NOT NULL,
    triggered_by    VARCHAR(10)     NOT NULL,
    reasoning       NVARCHAR(MAX)   NULL,
    created_at      DATETIME2       NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Action_Node       FOREIGN KEY (node_id)       REFERENCES Nodes(id),
    CONSTRAINT FK_Action_Telemetry  FOREIGN KEY (telemetry_id)  REFERENCES Telemetry(id)
);
GO

CREATE INDEX IX_ActionLogs_NodeId_CreatedAt
    ON Action_Logs (node_id, created_at DESC);
GO
