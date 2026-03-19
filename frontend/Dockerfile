FROM php:8.2-apache

# Dépendances système
RUN apt-get update && apt-get install -y \
    libzip-dev zip unzip git curl \
    && docker-php-ext-install pdo pdo_mysql zip

# Apache config Laravel
RUN a2enmod rewrite
RUN sed -i 's!/var/www/html!/var/www/html/public!g' /etc/apache2/sites-available/000-default.conf

# Limites upload PHP
RUN echo "upload_max_filesize=50M\npost_max_size=100M\nmax_file_uploads=20" \
    > /usr/local/etc/php/conf.d/uploads.ini

# Installer Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Copier uniquement les fichiers Composer (cache Docker)
COPY composer.json composer.lock ./

RUN composer install --no-scripts --no-autoloader

# Copier tout le projet
COPY . .

# Finaliser Laravel
RUN composer dump-autoload --optimize


# Permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2-foreground"]
