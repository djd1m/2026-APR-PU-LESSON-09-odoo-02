# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    libjpeg-dev \
    libfreetype6-dev \
    zlib1g-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libsasl2-2 \
    libldap-2.5-0 \
    libssl3 \
    libjpeg62-turbo \
    libfreetype6 \
    zlib1g \
    curl \
    node-less \
    npm \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Install rtlcss for Odoo RTL support
RUN npm install -g rtlcss

# Create odoo user
RUN useradd -m -d /var/lib/odoo -s /bin/bash odoo

# Copy Python dependencies from builder
COPY --from=builder /install /usr/local

# Install Odoo from source
ARG ODOO_VERSION=17.0
RUN git clone --depth 1 --branch ${ODOO_VERSION} \
    https://github.com/odoo/odoo.git /opt/odoo \
    && pip install --no-cache-dir -e /opt/odoo

# Copy custom addons
COPY custom-addons /mnt/extra-addons

# Copy Odoo configuration
COPY odoo.conf /etc/odoo/odoo.conf

# Set permissions
RUN chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons

# Volumes
VOLUME ["/var/lib/odoo", "/mnt/extra-addons"]

# Expose Odoo port
EXPOSE 8069

USER odoo

ENTRYPOINT ["odoo"]
CMD ["--config=/etc/odoo/odoo.conf", "--addons-path=/opt/odoo/addons,/mnt/extra-addons"]
