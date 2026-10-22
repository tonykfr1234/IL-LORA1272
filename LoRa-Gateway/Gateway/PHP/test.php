<?php
declare(strict_types=1);

// Retain the old diagnostic URL as a read-only JSON list, without separate credentials.
$_GET = ['action' => 'list'];
$_POST = [];
require __DIR__ . '/AjaxIoT.php';
