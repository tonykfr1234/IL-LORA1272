<?php
declare(strict_types=1);

define('INCLUDE_CHECK', true);
require __DIR__ . '/functions.php';

$con = null;
try {
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    if ($method !== 'GET' && $method !== 'POST') {
        header('Allow: GET, POST');
        throw new IotRequestException('Use GET or POST.', 405);
    }
    $input = array_merge($_GET, $_POST);
    $action = iot_string($input, 'action', 32);
    $actions = ['list', 'insertByAPIKey', 'insert', 'create', 'update', 'delete'];
    if (!in_array($action, $actions, true)) {
        throw new IotRequestException('Unknown action.');
    }
    if ($action !== 'list') {
        iot_require_api_key($input);
    }
    if (in_array($action, ['create', 'update', 'delete'], true) && $method !== 'POST') {
        header('Allow: POST');
        throw new IotRequestException('This action requires POST.', 405);
    }

    // PHP 8 connection failures must also return valid JSON, not fatal HTML output.
    require __DIR__ . '/connect.php';
    if ($action === 'list') {
        $records = $con->query("SELECT * FROM $IoTTable ORDER BY Id ASC")->fetch_all(MYSQLI_ASSOC);
        iot_json(['Result' => 'OK', 'TotalRecordCount' => count($records), 'Records' => $records]);
    } elseif (in_array($action, ['insertByAPIKey', 'insert', 'create'], true)) {
        $key = iot_string($input, 'KeyName', 50, $action === 'create' ? '' : null);
        $data = iot_string($input, 'Data', 50);
        $type = iot_string($input, 'Datatype', 20);
        $owner = $action === 'insertByAPIKey' ? 0 : iot_integer($input, 'OwnerId', 0);
        $project = $action === 'insertByAPIKey' ? 0 : iot_integer($input, 'IoTProjectsId', 0);
        $time = gmdate('Y-m-d H:i:s');
        $statement = iot_query(
            $con,
            "INSERT INTO $IoTTable (KeyName, Data, OwnerId, Datatype, IoTProjectsId, Datetime) VALUES (?, ?, ?, ?, ?, ?)",
            [$key, $data, $owner, $type, $project, $time]
        );
        $id = (int) $con->insert_id;
        $statement->close();
        $record = iot_record($con, $IoTTable, $id);
        if ($action !== 'create') {
            iot_keep_latest($con, $IoTTable, $owner, $project);
        }
        iot_json(['Result' => 'OK', 'Record' => $record]);
    } elseif ($action === 'update') {
        $id = iot_integer($input, 'Id', null, 1);
        $record = iot_record($con, $IoTTable, $id);
        $key = iot_string($input, 'KeyName', 50, $record['KeyName']);
        $data = iot_string($input, 'Data', 50);
        $type = iot_string($input, 'Datatype', 20);
        $owner = iot_integer($input, 'OwnerId');
        $project = iot_integer($input, 'IoTProjectsId');
        $time = iot_datetime($input);
        $statement = iot_query(
            $con,
            "UPDATE $IoTTable SET KeyName = ?, Data = ?, OwnerId = ?, Datatype = ?, IoTProjectsId = ?, Datetime = ? WHERE Id = ?",
            [$key, $data, $owner, $type, $project, $time, $id]
        );
        $statement->close();
        iot_json(['Result' => 'OK', 'Record' => iot_record($con, $IoTTable, $id)]);
    } else {
        $id = iot_integer($input, 'Id', null, 1);
        iot_record($con, $IoTTable, $id);
        $statement = iot_query($con, "DELETE FROM $IoTTable WHERE Id = ?", [$id]);
        $statement->close();
        iot_json(['Result' => 'OK']);
    }
} catch (IotRequestException $error) {
    iot_json(['Result' => 'ERROR', 'Message' => $error->getMessage()], $error->status);
} catch (Throwable $error) {
    // Do not return SQL, credentials, paths or connection details to HTTP clients.
    error_log('IoT request failed (' . get_class($error) . ', code ' . $error->getCode() . ').');
    iot_json(['Result' => 'ERROR', 'Message' => 'Database operation failed. Check server configuration and logs.'], 500);
} finally {
    if ($con instanceof mysqli) {
        $con->close();
    }
}
