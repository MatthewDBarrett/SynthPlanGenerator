(function () {
  function debounce(fn, wait) {
    let timer = null;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function setupPicker(picker) {
    const modeRadios = picker.querySelectorAll('input[name="mode"]');
    const newFields = picker.querySelector('.picker-new-fields');
    const existingFields = picker.querySelector('.picker-existing-fields');
    const searchInput = picker.querySelector('.existing-search');
    const resultsBox = picker.querySelector('.existing-search-results');
    const hiddenId = picker.querySelector('input[name="existing_id"]');
    const selectedBox = picker.querySelector('.existing-selected');
    const excludeId = picker.dataset.exclude || '';

    modeRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        const isExisting = picker.querySelector('input[name="mode"]:checked').value === 'existing';
        newFields.hidden = isExisting;
        existingFields.hidden = !isExisting;
      });
    });

    if (!searchInput) return;

    const runSearch = debounce(() => {
      const q = searchInput.value.trim();
      resultsBox.innerHTML = '';
      if (!q) return;
      fetch(`/api/people/search?q=${encodeURIComponent(q)}&exclude=${encodeURIComponent(excludeId)}`)
        .then((res) => res.json())
        .then((people) => {
          resultsBox.innerHTML = '';
          people.forEach((person) => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            const dates = person.birth_date ? ` (b. ${person.birth_date})` : '';
            item.textContent = person.name + dates;
            item.addEventListener('click', () => {
              hiddenId.value = person.id;
              selectedBox.textContent = `Selected: ${person.name}${dates}`;
              resultsBox.innerHTML = '';
              searchInput.value = '';
            });
            resultsBox.appendChild(item);
          });
        });
    }, 250);

    searchInput.addEventListener('input', runSearch);
  }

  document.querySelectorAll('.person-picker').forEach(setupPicker);
})();
