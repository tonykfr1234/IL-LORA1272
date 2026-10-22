<?php
declare(strict_types=1);

if (!defined('INCLUDE_CHECK')) {
    http_response_code(404);
    exit;
}

$tableName = iot_env('DB_TABLE', 'IoTTable');
if (preg_match('/^[A-Za-z_][A-Za-z0-9_]{0,63}$/D', $tableName) !== 1) {
    throw new IotRequestException('Invalid server table configuration.', 503);
}
// Identifiers cannot be bound; only this validated server-side identifier is interpolated.
$IoTTable = chr(96) . $tableName . chr(96);
$port = filter_var(iot_env('DB_PORT', '3306'), FILTER_VALIDATE_INT, [
    'options' => ['min_range' => 1, 'max_range' => 65535],
]);
if ($port === false) {
    throw new IotRequestException('Invalid server database port.', 503);
}
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$con = new mysqli(
    iot_env('DB_HOST', '127.0.0.1'),
    iot_env('DB_USER'),
    iot_env('DB_PASSWORD'),
    iot_env('DB_NAME', 'loragateway'),
    $port
);
$con->set_charset('utf8mb4');
$con->query("SET time_zone = '+00:00'");
