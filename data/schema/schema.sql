-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               11.8.8-MariaDB-ubu2404 - mariadb.org binary distribution
-- Server OS:                    debian-linux-gnu
-- HeidiSQL Version:             12.20.0.7320
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Dumping structure for table swfe.sw_alle_tabelle
CREATE TABLE IF NOT EXISTS `sw_alle_tabelle` (
  `product` varchar(64) NOT NULL,
  `sw_index` bigint(20) NOT NULL,
  `sachnummer_index` int(11) DEFAULT NULL,
  `serial` varchar(64) DEFAULT NULL,
  `rmeldenr` varchar(64) DEFAULT NULL,
  `rev` varchar(32) DEFAULT NULL,
  `mmjj` varchar(16) DEFAULT NULL,
  `pruefer` varchar(64) DEFAULT NULL,
  `aktion` varchar(64) DEFAULT NULL,
  `code` varchar(64) DEFAULT NULL,
  `platz` varchar(64) DEFAULT NULL,
  `datum` date DEFAULT NULL,
  `azeit` time DEFAULT NULL,
  `bzeit` time DEFAULT NULL,
  `i1` varchar(255) DEFAULT NULL,
  `t1` varchar(255) DEFAULT NULL,
  `i2` varchar(255) DEFAULT NULL,
  `i3` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`product`,`sw_index`),
  KEY `serial` (`serial`),
  KEY `datum` (`datum`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
