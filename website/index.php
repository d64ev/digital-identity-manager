<!DOCTYPE html>
<head>
	<?php include '$WEBSITE_DIR/head.php' ?>
</head>
<body>
<header>
	<?php include '$WEBSITE_DIR/header.php' ?>
</header>
<main>
	<div id="hero">
		<?php include '$WEBSITE_DIR/main-hero.php' ?>
   </div>
    <div id="main-content">
    <h2>Verifizierte Profile</h2>
    <?php
    $accounts_json = file_get_contents("accounts.json");
    $accounts = json_decode($accounts_json);
    foreach ($accounts as $key => $value) {
    ?>
        <p><a href="<?= $value->url ?>" rel="me" target="_blank"><?= ucwords($value->service) ?> (@<?= $value->name ?>)</a></p>
    <?php
        }
    ?>
    </div>
</main>
<footer>
	<?php include '$WEBSITE_DIR/footer.php' ?>
</footer>
</body>
</html>
