USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'SmartGarden_Core')
BEGIN
    ALTER DATABASE SmartGarden_Core SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE SmartGarden_Core;
END
GO

CREATE DATABASE SmartGarden_Core;
GO
USE SmartGarden_Core;
GO

CREATE TABLE Crop_Batches (
    batch_id VARCHAR(50) PRIMARY KEY,
    plant_type NVARCHAR(50) DEFAULT N'Cải thìa',
    planted_date DATETIME2 DEFAULT GETDATE(),
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE Telemetry_Master (
    record_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    timestamp DATETIME2 DEFAULT GETDATE(),
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    avg_soil FLOAT NOT NULL,
    light_lux FLOAT NOT NULL,
    co2_level FLOAT NOT NULL,
    camera_status VARCHAR(20) DEFAULT 'OFFLINE',
    leaf_wilting_score FLOAT NULL,
    leaf_color_state VARCHAR(20) NULL,
    disease_detected INT DEFAULT 0,
    CONSTRAINT FK_Telemetry_Batch FOREIGN KEY (batch_id) REFERENCES Crop_Batches(batch_id)
);

CREATE TABLE Action_Logs (
    log_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    trigger_source VARCHAR(50) NOT NULL,
    reason NVARCHAR(255) NULL,
    timestamp DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_Action_Batch FOREIGN KEY (batch_id) REFERENCES Crop_Batches(batch_id)
);

INSERT INTO Crop_Batches (batch_id, plant_type, planted_date, status) 
VALUES ('BATCH_TEST_01', N'Cai thia thi nghiem', GETDATE(), 'ACTIVE');

SELECT * FROM Telemetry_Master ORDER BY record_id DESC;
TRUNCATE TABLE Telemetry_Master;
