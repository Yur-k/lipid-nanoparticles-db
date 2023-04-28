ARG version=1.14.2
ARG modules_dir="/usr/lib/nginx/modules"

################################################################
# BUILDER
#
# Compile brotli and lua from source to use it in a standard
# NGINX image container.
################################################################

FROM debian:stable AS builder
# FROM nginx:1.14.2 as builder

ARG version
ARG modules_dir
ARG build_dir="/usr/share/tmp"

# Setup
RUN apt-get update
RUN \
  apt-get update 2>&1 > /dev/null && \
  apt-get install \
  curl \
  wget \
  make \
  git \
  build-essential \
  gcc \
  libpcre3 \
  libpcre3-dev \
  libssl-dev \
  zlib1g zlib1g-dev \
  libxslt-dev \
  libgd-dev\
  # libgd2-xpm-dev \
  libgeoip-dev \
  libpam-dev \
  -y 2>&1 > /dev/null
RUN mkdir -p ${build_dir}
RUN mkdir -p ${modules_dir}

# Download NGINX
RUN cd ${build_dir} \
  && wget https://nginx.org/download/nginx-${version}.tar.gz \
  && tar zxf nginx-${version}.tar.gz \
  && rm nginx-${version}.tar.gz 

# Download Modules
RUN cd ${build_dir} \
# Brotli
  && git clone --recursive https://github.com/google/ngx_brotli.git brotli

# Building nginx and Installing modules
RUN cd ${build_dir}/nginx-${version} \
  && ./configure \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --modules-path=/usr/lib/nginx/modules \
  --conf-path=/etc/nginx/nginx.conf \
  --error-log-path=/var/log/nginx/error.log \
  --http-log-path=/var/log/nginx/access.log \
  --pid-path=/var/run/nginx.pid \
  --lock-path=/var/run/nginx.lock \
  --http-client-body-temp-path=/var/cache/nginx/client_temp \
  --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
  --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
  --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
  --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
  --with-http_ssl_module \
  --with-http_realip_module \
  --with-http_addition_module \
  --with-http_sub_module \
  --with-http_dav_module \
  --with-http_flv_module \
  --with-http_mp4_module \
  --with-http_gunzip_module \
  --with-http_gzip_static_module \
  --with-http_random_index_module \
  --with-http_secure_link_module \
  --with-http_stub_status_module \
  --with-http_auth_request_module \
  --with-http_xslt_module=dynamic \
  --with-http_image_filter_module=dynamic \
  --with-threads \
  --with-stream \
  --with-stream_ssl_module \
  --with-stream_ssl_preread_module \
  --with-stream_realip_module \
  --with-stream_geoip_module=dynamic \
  --with-http_slice_module \
  --with-mail \
  --with-mail_ssl_module \
  --with-compat \
  --with-file-aio \
  --with-http_v2_module \  
  --with-compat \
  --add-dynamic-module=../brotli  \
  && make && make install

# Move compiled modules
RUN cd ${build_dir}/nginx-${version}/objs \
  && cp ngx_http_brotli_static_module.so ${modules_dir} \
  && cp ngx_http_brotli_filter_module.so ${modules_dir} \
  && chmod -R 644 ${modules_dir}

################################################################
# SERVER
################################################################

FROM nginx:${version}-alpine

ENV PATH /usr/sbin/nginx:$PATH
ARG modules_dir

# RUN \
#   apk update 2>&1 > dev/null && \
#   apk add openssl -y 2>&1 > /dev/null

RUN \
  mkdir -p /etc/nginx && \
  # mkdir -p /usr/sbin/nginx && \
  mkdir -p /var/cache/nginx && \
  mkdir -p /var/log/nginx && \
  mkdir -p /usr/lib/nginx/modules && \
  mkdir -p /etc/nginx/conf.d && \
  mkdir -p /etc/nginx/ssl

COPY --from=builder /usr/sbin/nginx /usr/sbin/
COPY --from=builder ${modules_dir}/* ${modules_dir}/
COPY --from=builder /etc/nginx/fastcgi.conf /etc/nginx/
COPY --from=builder /etc/nginx/*_params /etc/nginx/
COPY --from=builder /etc/nginx/koi-* /etc/nginx/
COPY --from=builder /etc/nginx/win-utf /etc/nginx/
COPY --from=builder /etc/nginx/mime.types /etc/nginx/

RUN ln -s /usr/lib/nginx/modules /etc/nginx/modules

RUN rm /etc/nginx/conf.d/default.conf
COPY --chown=root:root ./nginx.conf /etc/nginx/
COPY --chown=root:root ./sites-enabled /etc/nginx/sites-enabled

################################################################

EXPOSE 80
EXPOSE 443/tcp
EXPOSE 443/udp

CMD ["nginx-debug", "-g", "daemon off;"]