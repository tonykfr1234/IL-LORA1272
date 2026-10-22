-- Fresh installations only. The official image runs this once for a new volume.
-- Keep the legacy column names/types so existing sensor data remains compatible.
CREATE TABLE IF NOT EXISTS `IoTTable` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `Datetime` datetime NOT NULL,
  `KeyName` varchar(50) NOT NULL,
  `Data` varchar(50) NOT NULL,
  `OwnerId` int NOT NULL,
  `Datatype` varchar(20) NOT NULL,
  `IoTProjectsId` int NOT NULL DEFAULT 0,
  PRIMARY KEY (`Id`),
  KEY `owner_project_id` (`OwnerId`, `IoTProjectsId`, `Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
