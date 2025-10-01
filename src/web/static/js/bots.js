// ========== ГЛОБАЛЬНЫЕ onclick-функции ==========
function createBot() {
  try {
    const modalEl = document.getElementById('createBotModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
      new bootstrap.Modal(modalEl).show();
    } else {
      alert('createBot: откройте форму создания бота');
    }
  } catch (e) {
    console.error('createBot error:', e);
    alert('Ошибка createBot: ' + e.message);
  }
}

function showBotInfo(botId) {
  try {
    const modal = document.getElementById('botInfoModal');
    const titleEl = document.getElementById('botInfoModalLabel');
    const bodyEl = document.getElementById('botInfoModalBody');
    if (modal && titleEl && bodyEl && typeof bootstrap !== 'undefined') {
      titleEl.textContent = 'Информация о боте';
      bodyEl.textContent = 'Бот: ' + (botId || '(не указан)');
      new bootstrap.Modal(modal).show();
    } else {
      alert('Информация о боте: ' + (botId || '(не указан)'));
    }
  } catch (e) {
    console.error('showBotInfo error:', e);
    alert('Ошибка showBotInfo: ' + e.message);
  }
}

function refreshBots() {
  try {
    if (typeof window.updateBotsData === 'function') {
      window.updateBotsData();
    } else {
      location.reload();
    }
  } catch (e) {
    console.error('refreshBots error:', e);
    location.reload();
  }
}

function forceStopAllBots() {
  try {
    if (!confirm('Остановить ВСЕ боты?')) return;
    fetch('/api/bots/force-stop-all', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }
    })
      .then(r => r.json())
      .then(d => {
        if (d && d.success) {
          alert('Все боты остановлены');
          if (typeof window.updateBotsData === 'function') window.updateBotsData();
        } else {
          alert('Ошибка остановки: ' + (d && d.error ? d.error : 'неизвестно'));
        }
      })
      .catch(e => {
        console.error('forceStopAllBots error:', e);
        alert('Ошибка сети: ' + e.message);
      });
  } catch (e) {
    console.error('forceStopAllBots outer error:', e);
    alert('Ошибка: ' + e.message);
  }
}

// ========== РЕЗЕРВ: экспорт, если основные не были объявлены раньше ==========
(function () {
  function defineIfMissing(name, impl) {
    if (typeof window[name] !== 'function') {
      window[name] = impl;
      console.log(`[bots.js] Экспортирована резервная функция ${name}`);
    } else {
      console.log(`[bots.js] Функция ${name} уже определена — оставляем оригинал`);
    }
  }

  defineIfMissing('createBot', function () {
    try {
      if (typeof window.updateBotsData === 'function') {
        // Заглушка создания — просто просим пользователя заполнить форму/модалку
        const modalEl = document.getElementById('createBotModal');
        if (modalEl && typeof bootstrap !== 'undefined') {
          new bootstrap.Modal(modalEl).show();
        } else {
          alert('createBot: откройте форму создания бота');
        }
      } else {
        alert('createBot: функция UI ещё не загружена');
      }
    } catch (e) {
      console.error('createBot fallback error:', e);
      alert('Ошибка createBot: ' + e.message);
    }
  });

  defineIfMissing('showBotInfo', function (botType) {
    try {
      const title = botType === 'grid' ? 'Grid Bot' : 'Scalp Bot';
      const body = botType === 'grid'
        ? 'Grid Bot — сеточная стратегия. Стабильность в боковике.'
        : 'Scalp Bot — скальпинг. Частые сделки, выше требования к рискам.';
      const modal = document.getElementById('botInfoModal');
      const titleEl = document.getElementById('botInfoModalLabel');
      const bodyEl = document.getElementById('botInfoModalBody');
      if (modal && titleEl && bodyEl && typeof bootstrap !== 'undefined') {
        titleEl.textContent = title;
        bodyEl.textContent = body;
        new bootstrap.Modal(modal).show();
      } else {
        alert(`${title}: ${body}`);
      }
    } catch (e) {
      console.error('showBotInfo fallback error:', e);
      alert('Ошибка showBotInfo: ' + e.message);
    }
  });

  defineIfMissing('refreshBots', function () {
    try {
      if (typeof window.updateBotsData === 'function') {
        window.updateBotsData();
      } else {
        location.reload();
      }
    } catch (e) {
      console.error('refreshBots fallback error:', e);
      location.reload();
    }
  });

  defineIfMissing('forceStopAllBots', function () {
    try {
      if (!confirm('Остановить все боты?')) return;
      fetch('/api/bots/force-stop-all', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }
      })
        .then(r => r.json())
        .then(d => {
          if (d && d.success) {
            alert('Все боты остановлены');
            if (typeof window.updateBotsData === 'function') window.updateBotsData();
          } else {
            alert('Ошибка остановки: ' + (d && d.error ? d.error : 'неизвестно'));
          }
        })
        .catch(e => {
          console.error('forceStopAllBots fallback error:', e);
          alert('Ошибка сети: ' + e.message);
        });
    } catch (e) {
      console.error('forceStopAllBots fallback outer error:', e);
      alert('Ошибка: ' + e.message);
    }
  });
})();


