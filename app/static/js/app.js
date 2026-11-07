/**
 * Letterboxd & JustWatch Italia — Frontend Application Logic
 */

const state = {
  filterMode: 'available', // 'available', 'free', 'all', 'not_available'
  sortBy: 'date_added',
  sortOrder: 'desc',
  search: '',
  genre: 'all',
  activePlatforms: [],
  knownProviders: [],
  selectedCsvFile: null,
  scanPollTimer: null,
  searchDebounceTimer: null
};

// DOM Elements
const DOM = {
  statAvailable: document.getElementById('stat-available'),
  statFree: document.getElementById('stat-free'),
  statTotal: document.getElementById('stat-total'),
  statNotAvailable: document.getElementById('stat-not-available'),
  
  filterModeGroup: document.getElementById('filter-mode-group'),
  inputSearch: document.getElementById('input-search'),
  btnClearSearch: document.getElementById('btn-clear-search'),
  selectSortBy: document.getElementById('select-sort-by'),
  btnSortOrder: document.getElementById('btn-sort-order'),
  sortOrderIcon: document.getElementById('sort-order-icon'),
  selectGenre: document.getElementById('select-genre'),
  
  activePlatformsPills: document.getElementById('active-platforms-pills'),
  platformsCountPill: document.getElementById('platforms-count-pill'),
  
  moviesGrid: document.getElementById('movies-grid'),
  moviesLoading: document.getElementById('movies-loading'),
  moviesEmpty: document.getElementById('movies-empty'),
  emptyTitle: document.getElementById('empty-title'),
  emptyDesc: document.getElementById('empty-desc'),
  
  scanBanner: document.getElementById('scan-banner'),
  scanStatusMsg: document.getElementById('scan-status-msg'),
  scanProgressFill: document.getElementById('scan-progress-fill'),
  scanProgressNumbers: document.getElementById('scan-progress-numbers'),
  btnCancelScan: document.getElementById('btn-cancel-scan'),
  btnRefreshScan: document.getElementById('btn-refresh-scan'),
  btnClearWatchlist: document.getElementById('btn-clear-watchlist'),
  
  // Modals
  modalPlatforms: document.getElementById('modal-platforms'),
  modalImport: document.getElementById('modal-import'),
  btnOpenPlatforms: document.getElementById('btn-open-platforms'),
  btnEditActivePlatforms: document.getElementById('btn-edit-active-platforms'),
  btnOpenImport: document.getElementById('btn-open-import'),
  btnEmptyImport: document.getElementById('btn-empty-import'),
  
  // Platforms Modal
  platformsFreeGrid: document.getElementById('platforms-free-grid'),
  platformsSubGrid: document.getElementById('platforms-sub-grid'),
  platformsSpecialGrid: document.getElementById('platforms-special-grid'),
  btnSelectAllPlatforms: document.getElementById('btn-select-all-platforms'),
  btnDeselectAllPlatforms: document.getElementById('btn-deselect-all-platforms'),
  btnSelectFreeOnly: document.getElementById('btn-select-free-only'),
  btnSavePlatforms: document.getElementById('btn-save-platforms'),
  
  // Import Modal
  dropzoneCsv: document.getElementById('dropzone-csv'),
  inputCsvFile: document.getElementById('input-csv-file'),
  csvFileSelected: document.getElementById('csv-file-selected'),
  selectedFileName: document.getElementById('selected-file-name'),
  btnRemoveSelectedFile: document.getElementById('btn-remove-selected-file'),
  btnSubmitCsv: document.getElementById('btn-submit-csv'),
  checkAutoScanCsv: document.getElementById('check-auto-scan-csv'),
  
  inputUsername: document.getElementById('input-username'),
  checkAutoScanUser: document.getElementById('check-auto-scan-user'),
  btnSubmitUsername: document.getElementById('btn-submit-username'),
  
  inputSingleTitle: document.getElementById('input-single-title'),
  inputSingleYear: document.getElementById('input-single-year'),
  btnSubmitSingle: document.getElementById('btn-submit-single'),
  importMsg: document.getElementById('import-msg'),
  
  toastContainer: document.getElementById('toast-container')
};

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadPlatforms();
  loadStats();
  loadMovies();
  checkScanStatus();
});

function initEventListeners() {
  // Stat cards filter clicks
  document.querySelectorAll('.stat-card').forEach(card => {
    card.addEventListener('click', () => {
      const mode = card.dataset.filter;
      setFilterMode(mode);
    });
  });

  // Segmented control buttons
  DOM.filterModeGroup.querySelectorAll('.seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setFilterMode(btn.dataset.mode);
    });
  });

  // Search input
  DOM.inputSearch.addEventListener('input', (e) => {
    state.search = e.target.value;
    DOM.btnClearSearch.classList.toggle('hidden', !state.search);
    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(() => {
      loadMovies();
    }, 250);
  });

  DOM.btnClearSearch.addEventListener('click', () => {
    DOM.inputSearch.value = '';
    state.search = '';
    DOM.btnClearSearch.classList.add('hidden');
    loadMovies();
  });

  // Sort & Genre changes
  DOM.selectSortBy.addEventListener('change', (e) => {
    state.sortBy = e.target.value;
    loadMovies();
  });

  DOM.btnSortOrder.addEventListener('click', () => {
    state.sortOrder = (state.sortOrder === 'asc') ? 'desc' : 'asc';
    DOM.sortOrderIcon.textContent = state.sortOrder === 'asc' ? '⬆️' : '⬇️';
    loadMovies();
  });

  DOM.selectGenre.addEventListener('change', (e) => {
    state.genre = e.target.value;
    loadMovies();
  });

  // Modal open/close
  DOM.btnOpenPlatforms.addEventListener('click', () => openModal(DOM.modalPlatforms));
  DOM.btnEditActivePlatforms.addEventListener('click', () => openModal(DOM.modalPlatforms));
  DOM.btnOpenImport.addEventListener('click', () => openModal(DOM.modalImport));
  DOM.btnEmptyImport.addEventListener('click', () => openModal(DOM.modalImport));

  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.dataset.close;
      closeModal(document.getElementById(modalId));
    });
  });

  // Close modals on outside click
  [DOM.modalPlatforms, DOM.modalImport].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal);
    });
  });

  // Import tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
      hideImportMsg();
    });
  });

  // CSV Drag and drop
  initDropzone();

  // CSV submit
  DOM.btnSubmitCsv.addEventListener('click', handleCsvSubmit);

  // Username submit
  DOM.btnSubmitUsername.addEventListener('click', handleUsernameSubmit);

  // Single movie submit
  DOM.btnSubmitSingle.addEventListener('click', handleSingleMovieSubmit);

  // Platform bulk actions
  DOM.btnSelectAllPlatforms.addEventListener('click', () => toggleAllPlatforms(true));
  DOM.btnDeselectAllPlatforms.addEventListener('click', () => toggleAllPlatforms(false));
  DOM.btnSelectFreeOnly.addEventListener('click', selectOnlyFreePlatforms);
  DOM.btnSavePlatforms.addEventListener('click', handleSavePlatforms);

  // Scan actions
  DOM.btnRefreshScan.addEventListener('click', handleStartScan);
  DOM.btnCancelScan.addEventListener('click', handleCancelScan);
  DOM.btnClearWatchlist.addEventListener('click', handleClearWatchlist);
}

// -------------------------------------------------------------
// FILTER & STATS
// -------------------------------------------------------------

function setFilterMode(mode) {
  state.filterMode = mode;
  // Update segmented control
  DOM.filterModeGroup.querySelectorAll('.seg-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  // Update stat card active indicator
  document.querySelectorAll('.stat-card').forEach(card => {
    card.classList.toggle('active', card.dataset.filter === mode);
  });
  loadMovies();
}

async function loadStats() {
  try {
    const res = await fetch('/api/watchlist/stats');
    if (!res.ok) return;
    const data = await res.json();
    
    DOM.statAvailable.textContent = data.available_now || 0;
    DOM.statFree.textContent = data.free_count || 0;
    DOM.statTotal.textContent = data.total || 0;
    DOM.statNotAvailable.textContent = data.not_available || 0;

    // Populate genres dropdown if changed
    const currentGenre = DOM.selectGenre.value;
    DOM.selectGenre.innerHTML = '<option value="all">Tutti i generi</option>';
    (data.genres || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g;
      opt.textContent = g;
      if (g === currentGenre) opt.selected = true;
      DOM.selectGenre.appendChild(opt);
    });
  } catch (err) {
    console.error("Error loading stats:", err);
  }
}

// -------------------------------------------------------------
// MOVIES LIST & RENDERING
// -------------------------------------------------------------

async function loadMovies() {
  DOM.moviesLoading.classList.remove('hidden');
  DOM.moviesEmpty.classList.add('hidden');
  DOM.moviesGrid.innerHTML = '';

  const params = new URLSearchParams({
    filter_mode: state.filterMode,
    sort_by: state.sortBy,
    sort_order: state.sortOrder
  });
  if (state.search) params.append('search', state.search);
  if (state.genre && state.genre !== 'all') params.append('genre', state.genre);

  try {
    const res = await fetch(`/api/watchlist/movies?${params.toString()}`);
    if (!res.ok) throw new Error("Errore nel caricamento film");
    const data = await res.json();
    const movies = data.movies || [];

    DOM.moviesLoading.classList.add('hidden');

    if (movies.length === 0) {
      DOM.moviesEmpty.classList.remove('hidden');
      updateEmptyStateMessage();
      return;
    }

    DOM.moviesEmpty.classList.add('hidden');
    renderMovieCards(movies);
  } catch (err) {
    DOM.moviesLoading.classList.add('hidden');
    showToast(`Errore: ${err.message}`, 'error');
  }
}

function updateEmptyStateMessage() {
  if (state.search) {
    DOM.emptyTitle.textContent = `Nessun risultato per "${state.search}"`;
    DOM.emptyDesc.textContent = "Prova a cercare un altro titolo o svuota la barra di ricerca.";
  } else if (state.filterMode === 'available') {
    DOM.emptyTitle.textContent = "Nessun film disponibile subito";
    DOM.emptyDesc.textContent = "Nessun film della tua watchlist è attualmente in streaming sui tuoi abbonamenti o gratis. Prova a selezionare altre piattaforme o visualizza tutti i film.";
  } else if (state.filterMode === 'free') {
    DOM.emptyTitle.textContent = "Nessun film gratuito trovato";
    DOM.emptyDesc.textContent = "Al momento nessun film della tua watchlist è disponibile gratis su RaiPlay, Mediaset Infinity o Pluto TV.";
  } else {
    DOM.emptyTitle.textContent = "Watchlist vuota";
    DOM.emptyDesc.textContent = "Importa la tua watchlist di Letterboxd con il file CSV o il tuo username!";
  }
}

function renderMovieCards(movies) {
  const fragment = document.createDocumentFragment();

  movies.forEach(movie => {
    const card = document.createElement('article');
    card.className = 'movie-card';

    // Poster section
    const posterWrapper = document.createElement('div');
    posterWrapper.className = 'card-poster-wrapper';

    if (movie.poster_url) {
      const img = document.createElement('img');
      img.className = 'card-poster-img';
      img.src = movie.poster_url;
      img.alt = movie.title;
      img.loading = 'lazy';
      img.onerror = () => {
        img.remove();
        posterWrapper.appendChild(createPosterFallback(movie.title));
      };
      posterWrapper.appendChild(img);
    } else {
      posterWrapper.appendChild(createPosterFallback(movie.title));
    }

    // Top badges on poster
    const topBadges = document.createElement('div');
    topBadges.className = 'poster-badges-top';

    // IMDb score
    if (movie.imdb_score) {
      const imdbBadge = document.createElement('div');
      imdbBadge.className = 'badge-imdb';
      imdbBadge.innerHTML = `⭐ <span>${movie.imdb_score.toFixed(1)}</span>`;
      topBadges.appendChild(imdbBadge);
    } else {
      topBadges.appendChild(document.createElement('div'));
    }

    // Status badge
    const statusBadge = document.createElement('div');
    if (movie.is_available_now) {
      if (movie.has_free && movie.flatrate_user_offers.length === 0) {
        statusBadge.className = 'badge-status free-only';
        statusBadge.textContent = 'GRATIS';
      } else {
        statusBadge.className = 'badge-status available';
        statusBadge.textContent = 'SUBITO';
      }
    } else {
      statusBadge.className = 'badge-status not-available';
      statusBadge.textContent = movie.rent_buy_offers.length > 0 ? 'NOLEGGIO' : 'NON DISP.';
    }
    topBadges.appendChild(statusBadge);
    posterWrapper.appendChild(topBadges);
    card.appendChild(posterWrapper);

    // Card Body
    const body = document.createElement('div');
    body.className = 'card-body';

    // Title & Year
    const titleArea = document.createElement('div');
    titleArea.className = 'card-title-area';

    const titleH3 = document.createElement('h3');
    titleH3.className = 'card-title';
    titleH3.textContent = movie.jw_title || movie.title;
    titleH3.title = movie.title;
    titleArea.appendChild(titleH3);

    const meta = document.createElement('div');
    meta.className = 'card-meta';
    const displayYear = movie.release_year || movie.jw_year;
    if (displayYear) {
      const yearSpan = document.createElement('span');
      yearSpan.className = 'card-year';
      yearSpan.textContent = displayYear;
      meta.appendChild(yearSpan);
    }

    // Genre tags
    if (movie.genres && movie.genres.length > 0) {
      const genresWrap = document.createElement('div');
      genresWrap.className = 'card-genres';
      movie.genres.slice(0, 2).forEach(g => {
        const tag = document.createElement('span');
        tag.className = 'genre-tag';
        tag.textContent = g;
        genresWrap.appendChild(tag);
      });
      meta.appendChild(genresWrap);
    }
    titleArea.appendChild(meta);

    // Added Date
    if (movie.date_added) {
      const dateAddedSpan = document.createElement('div');
      dateAddedSpan.className = 'card-date-added';
      dateAddedSpan.textContent = `Aggiunto: ${formatDate(movie.date_added)}`;
      titleArea.appendChild(dateAddedSpan);
    }

    body.appendChild(titleArea);

    // Offers Section
    const offersSec = document.createElement('div');
    offersSec.className = 'card-offers-section';

    let hasAnyOffer = false;

    // 1. User active subscriptions (Flatrate)
    if (movie.flatrate_user_offers && movie.flatrate_user_offers.length > 0) {
      hasAnyOffer = true;
      const subGroup = document.createElement('div');
      subGroup.className = 'offers-sub-group';
      subGroup.innerHTML = `<span class="offers-group-title sub">🍿 Nei tuoi abbonamenti:</span>`;
      const list = document.createElement('div');
      list.className = 'offers-list';
      movie.flatrate_user_offers.forEach(off => {
        list.appendChild(createOfferBadge(off, false));
      });
      subGroup.appendChild(list);
      offersSec.appendChild(subGroup);
    }

    // 2. Free Italian / Ads platforms
    if (movie.free_offers && movie.free_offers.length > 0) {
      hasAnyOffer = true;
      const freeGroup = document.createElement('div');
      freeGroup.className = 'offers-free-group';
      freeGroup.innerHTML = `<span class="offers-group-title free">🆓 Disponibile Gratis:</span>`;
      const list = document.createElement('div');
      list.className = 'offers-list';
      movie.free_offers.forEach(off => {
        list.appendChild(createOfferBadge(off, true));
      });
      freeGroup.appendChild(list);
      offersSec.appendChild(freeGroup);
    }

    // 3. Other subscriptions (not currently active for user)
    if (movie.flatrate_other_offers && movie.flatrate_other_offers.length > 0 && !movie.is_available_now) {
      hasAnyOffer = true;
      const otherGroup = document.createElement('div');
      otherGroup.className = 'offers-other-group';
      otherGroup.innerHTML = `<span class="offers-group-title other">🔒 Altri servizi:</span>`;
      const list = document.createElement('div');
      list.className = 'offers-list';
      movie.flatrate_other_offers.slice(0, 3).forEach(off => {
        list.appendChild(createOfferBadge(off, false, true));
      });
      otherGroup.appendChild(list);
      offersSec.appendChild(otherGroup);
    }

    // 4. Rent / Buy indicator if no streaming
    if (!hasAnyOffer) {
      const notice = document.createElement('div');
      notice.className = 'no-offers-notice';
      if (movie.rent_buy_offers && movie.rent_buy_offers.length > 0) {
        notice.innerHTML = `💳 Disponibile a noleggio/acquisto (${movie.rent_buy_offers.length} store)`;
      } else if (movie.status === 'pending') {
        notice.innerHTML = `⏳ In attesa di verifica JustWatch...`;
      } else {
        notice.innerHTML = `❌ Non disponibile in streaming in Italia`;
      }
      offersSec.appendChild(notice);
    }

    body.appendChild(offersSec);

    // External Links (Letterboxd & JustWatch)
    const extLinks = document.createElement('div');
    extLinks.className = 'card-external-links';

    if (movie.letterboxd_uri) {
      const lbLink = document.createElement('a');
      lbLink.href = movie.letterboxd_uri;
      lbLink.target = '_blank';
      lbLink.rel = 'noopener';
      lbLink.className = 'card-link-item';
      lbLink.textContent = 'Letterboxd ↗';
      extLinks.appendChild(lbLink);
    }

    const jwQuery = encodeURIComponent(movie.jw_title || movie.title);
    const jwLink = document.createElement('a');
    jwLink.href = `https://www.justwatch.com/it/cerca?q=${jwQuery}`;
    jwLink.target = '_blank';
    jwLink.rel = 'noopener';
    jwLink.className = 'card-link-item';
    jwLink.textContent = 'JustWatch ↗';
    extLinks.appendChild(jwLink);

    body.appendChild(extLinks);
    card.appendChild(body);
    fragment.appendChild(card);
  });

  DOM.moviesGrid.appendChild(fragment);
}

function createPosterFallback(title) {
  const fallback = document.createElement('div');
  fallback.className = 'card-poster-fallback';
  fallback.innerHTML = `
    <div class="fallback-icon">🎞️</div>
    <span class="fallback-text">${title}</span>
  `;
  return fallback;
}

function createOfferBadge(offer, isFree = false, isOther = false) {
  const a = document.createElement('a');
  a.className = `offer-link-badge ${isFree ? 'is-free' : ''} ${isOther ? 'is-other' : ''}`;
  a.href = offer.web_url || '#';
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.title = `Guarda ${isFree ? 'gratis' : ''} su ${offer.provider_name}`;

  if (offer.provider_icon) {
    const icon = document.createElement('img');
    icon.className = 'provider-icon-img';
    icon.src = offer.provider_icon;
    icon.alt = offer.provider_name;
    icon.onerror = () => icon.remove();
    a.appendChild(icon);
  }

  const nameSpan = document.createElement('span');
  nameSpan.textContent = offer.provider_name;
  a.appendChild(nameSpan);

  const ext = document.createElement('span');
  ext.className = 'offer-badge-ext';
  ext.textContent = '↗';
  a.appendChild(ext);

  return a;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

// -------------------------------------------------------------
// PLATFORMS MANAGEMENT
// -------------------------------------------------------------

async function loadPlatforms() {
  try {
    const res = await fetch('/api/platforms');
    if (!res.ok) return;
    const data = await res.json();
    state.knownProviders = data.providers || [];
    state.activePlatforms = data.active_platforms || [];

    renderActivePlatformsPills();
    renderPlatformCheckboxes();
  } catch (err) {
    console.error("Error loading platforms:", err);
  }
}

function renderActivePlatformsPills() {
  DOM.activePlatformsPills.innerHTML = '';
  DOM.platformsCountPill.textContent = state.activePlatforms.length;

  state.activePlatforms.forEach(p => {
    const pill = document.createElement('span');
    pill.className = 'platform-pill';
    pill.textContent = p;
    DOM.activePlatformsPills.appendChild(pill);
  });
}

function renderPlatformCheckboxes() {
  DOM.platformsFreeGrid.innerHTML = '';
  DOM.platformsSubGrid.innerHTML = '';
  DOM.platformsSpecialGrid.innerHTML = '';

  state.knownProviders.forEach(p => {
    const label = document.createElement('label');
    label.className = `platform-checkbox-label ${p.is_active ? 'checked' : ''}`;

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = p.name;
    cb.checked = p.is_active;

    cb.addEventListener('change', () => {
      label.classList.toggle('checked', cb.checked);
    });

    label.appendChild(cb);

    const nameSpan = document.createElement('span');
    nameSpan.className = 'p-name';
    nameSpan.textContent = p.name;
    label.appendChild(nameSpan);

    if (p.is_italian) {
      const itBadge = document.createElement('span');
      itBadge.className = 'p-badge-it';
      itBadge.textContent = 'IT';
      label.appendChild(itBadge);
    }

    if (p.category === 'free') {
      DOM.platformsFreeGrid.appendChild(label);
    } else if (p.category === 'subscription') {
      DOM.platformsSubGrid.appendChild(label);
    } else {
      DOM.platformsSpecialGrid.appendChild(label);
    }
  });
}

function toggleAllPlatforms(checked) {
  const cbs = DOM.modalPlatforms.querySelectorAll('input[type="checkbox"]');
  cbs.forEach(cb => {
    cb.checked = checked;
    cb.closest('label').classList.toggle('checked', checked);
  });
}

function selectOnlyFreePlatforms() {
  toggleAllPlatforms(false);
  const freeCbs = DOM.platformsFreeGrid.querySelectorAll('input[type="checkbox"]');
  freeCbs.forEach(cb => {
    cb.checked = true;
    cb.closest('label').classList.add('checked');
  });
}

async function handleSavePlatforms() {
  const selected = [];
  const cbs = DOM.modalPlatforms.querySelectorAll('input[type="checkbox"]:checked');
  cbs.forEach(cb => selected.push(cb.value));

  try {
    const res = await fetch('/api/platforms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platforms: selected })
    });
    if (!res.ok) throw new Error("Errore nel salvataggio");

    state.activePlatforms = selected;
    renderActivePlatformsPills();
    closeModal(DOM.modalPlatforms);
    showToast("Preferenze piattaforme salvate con successo!", "success");

    loadStats();
    loadMovies();
  } catch (err) {
    showToast(`Errore: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// IMPORT WATCHLIST (CSV, USERNAME, SINGLE)
// -------------------------------------------------------------

function initDropzone() {
  const dz = DOM.dropzoneCsv;
  const fileInput = DOM.inputCsvFile;

  dz.addEventListener('click', (e) => {
    if (e.target !== DOM.btnRemoveSelectedFile) {
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      setSelectedCsvFile(fileInput.files[0]);
    }
  });

  DOM.btnRemoveSelectedFile.addEventListener('click', (e) => {
    e.stopPropagation();
    clearSelectedCsvFile();
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dz.addEventListener(eventName, (e) => {
      e.preventDefault();
      dz.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dz.addEventListener(eventName, (e) => {
      e.preventDefault();
      dz.classList.remove('dragover');
    });
  });

  dz.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      setSelectedCsvFile(files[0]);
    }
  });
}

function setSelectedCsvFile(file) {
  state.selectedCsvFile = file;
  DOM.selectedFileName.textContent = file.name;
  DOM.csvFileSelected.classList.remove('hidden');
  DOM.btnSubmitCsv.disabled = false;
  DOM.dropzoneCsv.querySelector('.dropzone-main-text').textContent = "File selezionato:";
}

function clearSelectedCsvFile() {
  state.selectedCsvFile = null;
  DOM.inputCsvFile.value = '';
  DOM.csvFileSelected.classList.add('hidden');
  DOM.btnSubmitCsv.disabled = true;
  DOM.dropzoneCsv.querySelector('.dropzone-main-text').textContent = "Trascina qui il file watchlist.csv";
}

async function handleCsvSubmit() {
  if (!state.selectedCsvFile) return;

  const formData = new FormData();
  formData.append('file', state.selectedCsvFile);
  formData.append('auto_scan', DOM.checkAutoScanCsv.checked);

  DOM.btnSubmitCsv.disabled = true;
  DOM.btnSubmitCsv.textContent = "Caricamento in corso...";
  hideImportMsg();

  try {
    const res = await fetch('/api/watchlist/import-csv', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Errore caricamento CSV");

    showImportMsg(data.message, 'success');
    showToast(data.message, 'success');
    clearSelectedCsvFile();

    loadStats();
    loadMovies();
    if (DOM.checkAutoScanCsv.checked) {
      startScanPolling();
    }
  } catch (err) {
    showImportMsg(err.message, 'error');
  } finally {
    DOM.btnSubmitCsv.disabled = false;
    DOM.btnSubmitCsv.textContent = "Carica Watchlist CSV";
  }
}

async function handleUsernameSubmit() {
  const username = DOM.inputUsername.value.trim();
  if (!username) {
    showImportMsg("Inserisci un username Letterboxd valido.", 'error');
    return;
  }

  DOM.btnSubmitUsername.disabled = true;
  DOM.btnSubmitUsername.textContent = "Download in corso...";
  hideImportMsg();

  try {
    const res = await fetch('/api/watchlist/import-username', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username,
        auto_scan: DOM.checkAutoScanUser.checked
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Errore importazione username");

    showImportMsg(data.message, 'success');
    showToast(data.message, 'success');
    DOM.inputUsername.value = '';

    loadStats();
    loadMovies();
    if (DOM.checkAutoScanUser.checked) {
      startScanPolling();
    }
  } catch (err) {
    showImportMsg(err.message, 'error');
  } finally {
    DOM.btnSubmitUsername.disabled = false;
    DOM.btnSubmitUsername.textContent = "Scarica Watchlist da Profilo";
  }
}

async function handleSingleMovieSubmit() {
  const title = DOM.inputSingleTitle.value.trim();
  const year = DOM.inputSingleYear.value ? parseInt(DOM.inputSingleYear.value) : null;
  if (!title) {
    showImportMsg("Inserisci il titolo del film.", 'error');
    return;
  }

  DOM.btnSubmitSingle.disabled = true;
  hideImportMsg();

  try {
    const res = await fetch('/api/watchlist/add-movie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, year })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Errore aggiunta film");

    showImportMsg(`Film aggiunto con successo: ${title}`, 'success');
    showToast(`Aggiunto: ${title}`, 'success');
    DOM.inputSingleTitle.value = '';
    DOM.inputSingleYear.value = '';

    loadStats();
    loadMovies();
    startScanPolling();
  } catch (err) {
    showImportMsg(err.message, 'error');
  } finally {
    DOM.btnSubmitSingle.disabled = false;
  }
}

function showImportMsg(text, type) {
  DOM.importMsg.textContent = text;
  DOM.importMsg.className = `import-msg ${type}`;
  DOM.importMsg.classList.remove('hidden');
}

function hideImportMsg() {
  DOM.importMsg.classList.add('hidden');
}

// -------------------------------------------------------------
// SCANNING (SYNC WITH JUSTWATCH)
// -------------------------------------------------------------

async function handleStartScan() {
  try {
    const res = await fetch('/api/scan/start?force=true', { method: 'POST' });
    const data = await res.json();
    showToast(data.message, 'success');
    startScanPolling();
  } catch (err) {
    showToast(`Errore: ${err.message}`, 'error');
  }
}

async function handleCancelScan() {
  try {
    await fetch('/api/scan/cancel', { method: 'POST' });
    showToast("Interruzione richiesta...", "warning");
  } catch (err) {
    console.error("Cancel scan error:", err);
  }
}

function startScanPolling() {
  if (state.scanPollTimer) clearInterval(state.scanPollTimer);
  DOM.scanBanner.classList.remove('hidden');
  checkScanStatus();
  state.scanPollTimer = setInterval(checkScanStatus, 1000);
}

async function checkScanStatus() {
  try {
    const res = await fetch('/api/scan/progress');
    if (!res.ok) return;
    const progress = await res.json();

    if (progress.is_scanning) {
      DOM.scanBanner.classList.remove('hidden');
      DOM.scanStatusMsg.textContent = progress.status;
      DOM.scanProgressNumbers.textContent = `${progress.current} / ${progress.total}`;
      DOM.scanProgressFill.style.width = `${progress.percentage}%`;
    } else {
      if (state.scanPollTimer) {
        clearInterval(state.scanPollTimer);
        state.scanPollTimer = null;
        DOM.scanBanner.classList.add('hidden');
        loadStats();
        loadMovies();
      }
    }
  } catch (err) {
    console.error("Error polling scan progress:", err);
  }
}

async function handleClearWatchlist() {
  if (!confirm("Sei sicuro di voler svuotare tutta la watchlist e i relativi dati di JustWatch?")) {
    return;
  }
  try {
    const res = await fetch('/api/watchlist/clear', { method: 'DELETE' });
    if (!res.ok) throw new Error("Errore durante l'eliminazione");
    showToast("Watchlist svuotata con successo.", "success");
    loadStats();
    loadMovies();
  } catch (err) {
    showToast(`Errore: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// MODALS & TOASTS
// -------------------------------------------------------------

function openModal(modal) {
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';
  if (type === 'warning') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  DOM.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
