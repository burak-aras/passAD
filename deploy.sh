#!/bin/bash

# Hata durumunda dur
set -e

echo "🛑 Mevcut konteynerlar durduruluyor..."
docker-compose down

echo "🔥 Aggressive Cleanup: Tüm kullanılmayan imajlar ve containerlar siliniyor (Prune)..."
# -a: Sadece dangling değil, kullanılmayan TÜM imajları siler
# -f: Onay istemeden zorla siler
# --volumes: Kullanılmayan volume'leri de siler (Dikkat: Veri kaybı olabilir, o yüzden volume flagini kapalı tutuyorum. İsterseniz ekleyin.)
docker system prune -a -f

echo "🚀 Uygulama ve servisler sıfırdan derleniyor ve başlatılıyor..."
# --build: Yeniden build et
# -d: Arka planda çalıştır
docker-compose up -d --build

echo "✅ İşlem tamamlandı!"
echo "---------------------------------------------------"
echo "🌐 Web Arayüzü: http://localhost (veya sunucu IP'si)"
echo "⏰ Cron Job Servisi: Aktif"
echo "---------------------------------------------------"
