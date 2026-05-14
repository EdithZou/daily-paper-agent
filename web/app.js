const API_BASE = 'https://daily-paper-agent.tzou.workers.dev';
const STORAGE_KEY = 'daily_paper_subscription_v1';

const ARXIV_CATEGORIES = [
  { id: 'cs.AI',   label: 'cs.AI · 人工智能' },
  { id: 'cs.CL',   label: 'cs.CL · 自然语言处理' },
  { id: 'cs.LG',   label: 'cs.LG · 机器学习' },
  { id: 'cs.CV',   label: 'cs.CV · 计算机视觉' },
  { id: 'cs.IR',   label: 'cs.IR · 信息检索' },
  { id: 'cs.NE',   label: 'cs.NE · 神经/进化计算' },
  { id: 'cs.RO',   label: 'cs.RO · 机器人' },
  { id: 'cs.HC',   label: 'cs.HC · 人机交互' },
  { id: 'cs.CR',   label: 'cs.CR · 安全密码' },
  { id: 'stat.ML', label: 'stat.ML · 统计机器学习' },
];

const CHIP_ON  = ['bg-slate-900', 'text-white', 'border-slate-900'];
const CHIP_OFF = ['bg-white', 'text-slate-700', 'border-slate-300', 'hover:border-slate-500'];

function renderChips(selected) {
  const container = document.getElementById('category-chips');
  container.innerHTML = ARXIV_CATEGORIES.map((c) => {
    const active = selected.includes(c.id);
    const cls = active ? CHIP_ON.join(' ') : CHIP_OFF.join(' ');
    return `<button type="button" data-id="${c.id}"
      class="chip px-3 py-1.5 rounded-full text-sm border transition ${cls}">
      ${c.label}
    </button>`;
  }).join('');
  container.querySelectorAll('.chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const isOn = btn.classList.contains('bg-slate-900');
      if (isOn) {
        btn.classList.remove(...CHIP_ON);
        btn.classList.add(...CHIP_OFF);
      } else {
        btn.classList.remove(...CHIP_OFF);
        btn.classList.add(...CHIP_ON);
      }
    });
  });
}

function getSelectedCategories() {
  return Array.from(document.querySelectorAll('#category-chips .chip'))
    .filter((b) => b.classList.contains('bg-slate-900'))
    .map((b) => b.dataset.id);
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveToStorage(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function showToast(message, ok = true) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.classList.remove('hidden', 'bg-emerald-600', 'bg-red-600');
  el.classList.add(ok ? 'bg-emerald-600' : 'bg-red-600');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.add('hidden'), 3500);
}

function hydrate(existing) {
  const f = document.getElementById('subscribe-form');
  f.email.value             = existing.email             ?? '';
  f.telegram_chat_id.value  = existing.telegram_chat_id  ?? '';
  f.serverchan_key.value    = existing.serverchan_key    ?? '';
  f.keywords.value          = existing.keywords          ?? '';
  f.delivery_time.value     = existing.delivery_time     ?? '09:00';
  f.top_n.value             = existing.top_n             ?? 10;
  f.timezone.value          = existing.timezone          ?? 'Asia/Shanghai';
  f.summary_lang.value      = existing.summary_lang      ?? 'zh';
}

function collectFormData() {
  const fd = new FormData(document.getElementById('subscribe-form'));
  return {
    email:            fd.get('email')?.trim(),
    telegram_chat_id: fd.get('telegram_chat_id')?.trim() || null,
    serverchan_key:   fd.get('serverchan_key')?.trim() || null,
    categories:       getSelectedCategories(),
    keywords:         fd.get('keywords')?.trim() ?? '',
    delivery_time:    fd.get('delivery_time'),
    top_n:            Number(fd.get('top_n')),
    timezone:         fd.get('timezone'),
    summary_lang:     fd.get('summary_lang'),
  };
}

async function submitToBackend(data) {
  const r = await fetch(`${API_BASE}/api/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => r.statusText);
    throw new Error(text || `HTTP ${r.status}`);
  }
  return r.json().catch(() => ({}));
}

function init() {
  const existing = loadFromStorage();
  const initialCats = existing?.categories?.length
    ? existing.categories
    : ['cs.CL', 'cs.LG', 'cs.AI'];
  renderChips(initialCats);
  if (existing) hydrate(existing);

  if (API_BASE) {
    document.getElementById('backend-status').remove();
  }

  document.getElementById('subscribe-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = collectFormData();

    if (data.categories.length === 0) {
      showToast('请至少选择一个 arXiv 分类', false);
      return;
    }

    saveToStorage(data);

    if (!API_BASE) {
      showToast('已保存到本地（后端待部署）');
      return;
    }

    try {
      await submitToBackend(data);
      showToast('订阅成功，明天起每天准时送达');
    } catch (err) {
      showToast(`后端调用失败：${err.message}`, false);
    }
  });
}

init();
