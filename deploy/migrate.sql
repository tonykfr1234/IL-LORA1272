-- Run manually after backing up and importing an existing IoTTable.
-- Pause sensor writes first. This preserves rows, Id values and AUTO_INCREMENT.
-- If DB_TABLE was customized, review and replace the identifier below first.
-- This ALTER rebuilds the table and may require additional disk space.
ALTER TABLE `IoTTable`
  ENGINE=InnoDB,
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
