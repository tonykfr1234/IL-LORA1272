# Verified official multi-platform manifest, 2026-10-22.
FROM php:8.4.27-apache-bookworm@sha256:e653ff90d7f6e2e6f81eddb07c864f1eae224ccbf5143f82a44f25e2f110e320

RUN docker-php-ext-install -j "$(nproc)" mysqli \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && a2enmod headers

COPY deploy/php.ini /usr/local/etc/php/conf.d/gateway.ini
COPY deploy/apache.conf /etc/apache2/sites-available/000-default.conf
COPY LoRa-Gateway/Gateway/PHP/ /var/www/html/
COPY Demos_sourceCode/01_2017CES_TsuNaMi/Gateway/PHP/ /var/www/html/ces/

RUN php -r 'exit(PHP_VERSION === "8.4.27" && extension_loaded("mysqli") ? 0 : 1);'

EXPOSE 80
