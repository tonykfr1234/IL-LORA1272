<?php
declare(strict_types=1);

if (!defined('INCLUDE_CHECK')) {
    http_response_code(404);
    exit;
}

final class IotRequestException extends RuntimeException
{
    public function __construct(string $message, public readonly int $status = 400)
    {
        parent::__construct($message);
    }
}

function iot_env(string $name, ?string $default = null): string
{
    $value = getenv($name);
    if ($value === false || $value === '') {
        if ($default !== null) {
            return $default;
        }
        throw new IotRequestException('Server configuration is incomplete.', 503);
    }
    return $value;
}

function iot_string(array $input, string $name, int $maxLength, ?string $default = null): string
{
    if (!array_key_exists($name, $input)) {
        if ($default !== null) {
            return $default;
        }
        throw new IotRequestException('Missing field: ' . $name);
    }
    $value = $input[$name];
    if (!is_string($value) || preg_match('//u', $value) !== 1) {
        throw new IotRequestException('Invalid field: ' . $name);
    }
    if (preg_match_all('/./us', $value) > $maxLength) {
        throw new IotRequestException('Field is too long: ' . $name);
    }
    return $value;
}

function iot_integer(array $input, string $name, ?int $default = null, int $minimum = 0): int
{
    if (!array_key_exists($name, $input)) {
        if ($default !== null) {
            return $default;
        }
        throw new IotRequestException('Missing field: ' . $name);
    }
    $value = $input[$name];
    if (!is_string($value) || preg_match('/^[0-9]+$/D', $value) !== 1) {
        throw new IotRequestException('Invalid integer: ' . $name);
    }
    $value = filter_var($value, FILTER_VALIDATE_INT, [
        'options' => ['min_range' => $minimum, 'max_range' => 2147483647],
    ]);
    if ($value === false) {
        throw new IotRequestException('Integer is out of range: ' . $name);
    }
    return $value;
}

function iot_datetime(array $input): string
{
    $value = iot_string($input, 'Datetime', 19);
    $date = DateTimeImmutable::createFromFormat('!Y-m-d H:i:s', $value);
    if ($date === false || $date->format('Y-m-d H:i:s') !== $value) {
        throw new IotRequestException('Invalid Datetime; use YYYY-MM-DD HH:MM:SS.');
    }
    return $value;
}

function iot_require_api_key(array $input): void
{
    $expected = iot_env('IOT_API_KEY');
    if (strlen($expected) < 32) {
        throw new IotRequestException('Server API key must contain at least 32 characters.', 503);
    }
    $provided = $_SERVER['HTTP_X_API_KEY'] ?? ($input['APIKey'] ?? '');
    if (!is_string($provided) || !hash_equals($expected, $provided)) {
        throw new IotRequestException('A valid API key is required.', 403);
    }
}

function iot_query(mysqli $connection, string $sql, array $parameters = []): mysqli_stmt
{
    $statement = $connection->prepare($sql);
    // Request values are bound by the driver, never interpolated into SQL.
    $statement->execute($parameters);
    return $statement;
}

function iot_record(mysqli $connection, string $table, int $id): array
{
    $statement = iot_query($connection, "SELECT * FROM $table WHERE Id = ?", [$id]);
    $record = $statement->get_result()->fetch_assoc();
    $statement->close();
    if ($record === null) {
        throw new IotRequestException('Record not found.', 404);
    }
    return $record;
}

function iot_keep_latest(mysqli $connection, string $table, int $owner, int $project): void
{
    $statement = iot_query(
        $connection,
        "SELECT Id FROM $table WHERE OwnerId = ? AND IoTProjectsId = ? ORDER BY Id DESC LIMIT 1 OFFSET 49",
        [$owner, $project]
    );
    $cutoff = $statement->get_result()->fetch_assoc();
    $statement->close();
    if ($cutoff !== null) {
        // Another owner/project must not lose records when this device sends data.
        $statement = iot_query(
            $connection,
            "DELETE FROM $table WHERE OwnerId = ? AND IoTProjectsId = ? AND Id < ?",
            [$owner, $project, $cutoff['Id']]
        );
        $statement->close();
    }
}

function iot_json(array $result, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE | JSON_THROW_ON_ERROR);
}
