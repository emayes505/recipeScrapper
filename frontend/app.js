const statusMessages = {
  success: ['Recipe imported', 'The recipe is ready in your collection.'],
  queued: ['Import queued', 'Fetching the recipe now. This page will update when it is ready.'],
  processing: ['Importing recipe', 'Reading the recipe details now.'],
  duplicate: ['Recipe already saved', 'This recipe is already in your collection.'],
  missing: ['No link found', 'Share a web address that begins with http or https.'],
  invalid: ['Recipe not recognized', 'The page did not contain readable recipe data.'],
  failed: ['Import failed', 'The recipe could not be saved. Try again shortly.'],
};

function displayImportStatus(result, detail) {
  const message = statusMessages[result];
  if (!message) return;

  const status = document.querySelector('#status');
  status.className = `status status--${result}`;
  status.replaceChildren();

  const heading = document.createElement('strong');
  heading.textContent = message[0];
  const description = document.createElement('span');
  description.textContent = detail || message[1];
  status.append(heading, description);
  status.hidden = false;
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function showImportStatus() {
  const params = new URLSearchParams(window.location.search);
  const result = params.get('share');
  const importId = params.get('import_id');

  displayImportStatus(result);
  window.history.replaceState({}, '', '/');

  if (result !== 'queued' || !importId) return;

  for (let attempt = 0; attempt < 30; attempt += 1) {
    await wait(2000);
    try {
      const response = await fetch(`/api/imports/${encodeURIComponent(importId)}`);
      if (!response.ok) throw new Error(`Import API returned ${response.status}`);

      const recipeImport = await response.json();
      displayImportStatus(recipeImport.status, recipeImport.error_message);
      if (recipeImport.status === 'success' || recipeImport.status === 'duplicate') {
        loadRecipes();
        return;
      }
      if (recipeImport.status === 'invalid' || recipeImport.status === 'failed') return;
    } catch (error) {
      console.error(error);
      displayImportStatus('failed', 'The import status could not be checked. Refresh this page shortly.');
      return;
    }
  }

  displayImportStatus('processing', 'The recipe is still being fetched. Refresh this page shortly.');
}

function recipeRow(recipe) {
  const totalTime = (recipe.prep_time_min || 0) + (recipe.cook_time_min || 0);
  const details = [
    totalTime ? `${totalTime} min` : null,
    recipe.servings ? `${recipe.servings} servings` : null,
  ].filter(Boolean);

  const row = document.createElement('article');
  row.className = 'recipe-row';
  const openRecipe = document.createElement('button');
  openRecipe.className = 'recipe-row__open';
  openRecipe.type = 'button';
  openRecipe.addEventListener('click', () => {
    window.location.hash = `recipe-${recipe.id}`;
  });

  const date = document.createElement('span');
  date.className = 'recipe-row__date';
  const dateValue = recipe.created_at ? new Date(recipe.created_at) : null;
  date.textContent = dateValue && !Number.isNaN(dateValue.valueOf())
    ? dateValue.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    : 'Saved recipe';

  const content = document.createElement('span');
  content.className = 'recipe-row__content';
  const title = document.createElement('strong');
  title.textContent = recipe.title;
  content.append(title);

  if (details.length) {
    const meta = document.createElement('span');
    meta.className = 'recipe-meta';
    meta.textContent = details.join(' / ');
    content.append(meta);
  }

  const rating = document.createElement('span');
  rating.className = 'recipe-row__rating';
  rating.setAttribute('role', 'img');
  rating.setAttribute('aria-label', recipe.rating ? `Rated ${recipe.rating} out of 10` : 'Not rated');
  rating.textContent = Array.from({ length: 10 }, (_, index) => (
    recipe.rating && index < recipe.rating ? '★' : '☆'
  )).join('');
  content.append(rating);

  const arrow = document.createElement('span');
  arrow.className = 'recipe-row__arrow';
  arrow.setAttribute('aria-hidden', 'true');
  arrow.textContent = '›';
  openRecipe.append(date, content, arrow);

  const remove = document.createElement('button');
  remove.className = 'recipe-row__delete';
  remove.type = 'button';
  remove.textContent = 'Delete';
  remove.addEventListener('click', async () => {
    if (!window.confirm('Are you sure you want to delete?')) return;
    try {
      const response = await fetch(`/api/recipes/${recipe.id}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(`Recipe API returned ${response.status}`);
      loadRecipes();
    } catch (error) {
      console.error(error);
      window.alert('The recipe could not be deleted.');
    }
  });

  row.append(openRecipe, remove);
  return row;
}

async function loadRecipes() {
  const list = document.querySelector('#recipe-list');
  const count = document.querySelector('#recipe-count');

  try {
    const response = await fetch('/api/recipes');
    if (!response.ok) throw new Error(`Recipe API returned ${response.status}`);
    const recipes = await response.json();
    count.textContent = `${recipes.length} saved`;
    list.replaceChildren(...recipes.map(recipeRow));

    if (!recipes.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No recipes yet.';
      list.append(empty);
    }
  } catch (error) {
    console.error(error);
    list.innerHTML = '<p class="empty-state">Recipes are unavailable.</p>';
  }
}

function recipeIdFromHash() {
  const match = /^#recipe-(\d+)$/.exec(window.location.hash);
  return match ? Number(match[1]) : null;
}

function showCollection() {
  document.querySelector('#collection-view').hidden = false;
  document.querySelector('#recipe-view').hidden = true;
  document.title = 'Pi Cookbook';
}

function recipeMeta(recipe) {
  const values = [
    recipe.prep_time_min ? `Prep ${recipe.prep_time_min} min` : null,
    recipe.cook_time_min ? `Cook ${recipe.cook_time_min} min` : null,
    recipe.servings ? `${recipe.servings} servings` : null,
  ].filter(Boolean);
  const list = document.createElement('ul');
  list.className = 'recipe-detail__meta';
  values.forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    list.append(item);
  });
  return list;
}

function recipeRating(recipeId, score) {
  const rating = document.createElement('div');
  rating.className = 'recipe-rating';
  rating.setAttribute('aria-label', score ? `Rated ${score} out of 10` : 'Not rated');

  for (let value = 1; value <= 10; value += 1) {
    const star = document.createElement('button');
    star.className = 'recipe-rating__star';
    star.type = 'button';
    star.textContent = score && value <= score ? '★' : '☆';
    star.setAttribute('aria-label', `Rate ${value} out of 10`);
    star.setAttribute('aria-pressed', String(value === score));
    star.addEventListener('click', async () => {
      try {
        const response = await fetch(`/api/recipes/${recipeId}/rating`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ score: value }),
        });
        if (!response.ok) throw new Error(`Rating API returned ${response.status}`);
        showRecipe(recipeId);
      } catch (error) {
        console.error(error);
        window.alert('The rating could not be saved.');
      }
    });
    rating.append(star);
  }
  return rating;
}

function noteEntry(recipeId, note) {
  const entry = document.createElement('article');
  entry.className = 'note-entry';
  const heading = document.createElement('div');
  heading.className = 'note-entry__heading';
  const label = document.createElement('span');
  label.textContent = 'Note';
  const date = document.createElement('time');
  const dateValue = note.created_at ? new Date(note.created_at) : null;
  date.textContent = dateValue && !Number.isNaN(dateValue.valueOf())
    ? `Added ${dateValue.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`
    : 'Added date unavailable';
  heading.append(label, date);
  const text = document.createElement('p');
  text.textContent = note.note_text;
  const actions = document.createElement('div');
  actions.className = 'note-entry__actions';

  const edit = document.createElement('button');
  edit.type = 'button';
  edit.textContent = 'Edit';
  edit.addEventListener('click', () => {
    const input = document.createElement('textarea');
    input.value = note.note_text;
    input.rows = 3;
    const save = document.createElement('button');
    save.type = 'button';
    save.textContent = 'Save';
    save.addEventListener('click', async () => {
      try {
        const response = await fetch(`/api/recipes/${recipeId}/notes/${note.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ note_text: input.value }),
        });
        if (!response.ok) throw new Error(`Notes API returned ${response.status}`);
        showRecipe(recipeId);
      } catch (error) {
        console.error(error);
        window.alert('The note could not be updated.');
      }
    });
    entry.replaceChildren(input, save);
  });

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.textContent = 'Delete';
  remove.addEventListener('click', async () => {
    try {
      const response = await fetch(`/api/recipes/${recipeId}/notes/${note.id}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(`Notes API returned ${response.status}`);
      showRecipe(recipeId);
    } catch (error) {
      console.error(error);
      window.alert('The note could not be deleted.');
    }
  });

  actions.append(edit, remove);
  entry.append(heading, text, actions);
  return entry;
}

function recipeNotes(recipeId, notes) {
  const section = document.createElement('section');
  section.className = 'notes-panel';
  const title = document.createElement('h2');
  title.textContent = 'Notes';
  const form = document.createElement('form');
  const input = document.createElement('textarea');
  input.name = 'note';
  input.rows = 4;
  input.placeholder = 'Add a change, substitution, or reminder...';
  input.required = true;
  const submit = document.createElement('button');
  submit.type = 'submit';
  submit.textContent = 'Add note';
  form.append(input, submit);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(`/api/recipes/${recipeId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_text: input.value }),
      });
      if (!response.ok) throw new Error(`Notes API returned ${response.status}`);
      showRecipe(recipeId);
    } catch (error) {
      console.error(error);
      window.alert('The note could not be saved.');
    }
  });

  const list = document.createElement('div');
  list.className = 'notes-list';
  list.append(...notes.map((note) => noteEntry(recipeId, note)));
  section.append(title, form, list);
  return section;
}

async function showRecipe(recipeId) {
  const collection = document.querySelector('#collection-view');
  const view = document.querySelector('#recipe-view');
  collection.hidden = true;
  view.hidden = false;
  view.replaceChildren();

  const back = document.createElement('button');
  back.className = 'back-button';
  back.type = 'button';
  back.textContent = 'Back to recipes';
  back.addEventListener('click', () => { window.location.hash = ''; });

  const detailActions = document.createElement('div');
  detailActions.className = 'recipe-detail__actions';
  const print = document.createElement('button');
  print.className = 'print-button';
  print.type = 'button';
  print.setAttribute('aria-label', 'Print recipe');
  print.title = 'Print recipe';
  print.textContent = '🖨';
  print.addEventListener('click', () => {
    window.print();
  });
  detailActions.append(back, print);
  view.append(detailActions);

  try {
    const response = await fetch(`/api/recipes/${recipeId}`);
    if (!response.ok) throw new Error(`Recipe API returned ${response.status}`);
    const recipe = await response.json();
    document.title = `${recipe.title} | Pi Cookbook`;

    const heading = document.createElement('header');
    heading.className = 'recipe-detail__heading';
    const eyebrow = document.createElement('p');
    eyebrow.className = 'eyebrow';
    eyebrow.textContent = 'Recipe';
    const title = document.createElement('h1');
    title.textContent = recipe.title;
    heading.append(eyebrow, title, recipeRating(recipe.id, recipe.rating), recipeMeta(recipe));
    view.append(heading);

    const content = document.createElement('div');
    content.className = 'recipe-detail__content';

    const ingredients = document.createElement('section');
    ingredients.className = 'ingredients-panel';
    const ingredientsTitle = document.createElement('h2');
    ingredientsTitle.textContent = 'Ingredients';
    const ingredientsList = document.createElement('ul');
    recipe.ingredients.forEach((ingredient) => {
      const item = document.createElement('li');
      item.textContent = ingredient.raw_text || `${ingredient.quantity} ${ingredient.unit} ${ingredient.name}`;
      ingredientsList.append(item);
    });
    ingredients.append(ingredientsTitle, ingredientsList);

    const instructions = document.createElement('section');
    instructions.className = 'instructions-panel';
    const instructionsTitle = document.createElement('h2');
    instructionsTitle.textContent = 'Instructions';
    const instructionsText = document.createElement('p');
    instructionsText.textContent = recipe.instructions;
    instructions.append(instructionsTitle, instructionsText);
    content.append(ingredients, instructions);
    view.append(content);

    if (recipe.source_url) {
      const source = document.createElement('a');
      source.className = 'source-link';
      source.href = recipe.source_url;
      source.target = '_blank';
      source.rel = 'noopener noreferrer';
      source.textContent = 'Open original recipe';
      view.append(source);
    }

    view.append(recipeNotes(recipe.id, recipe.notes));
  } catch (error) {
    console.error(error);
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = 'This recipe is unavailable.';
    view.append(message);
  }
}

function updateView() {
  const recipeId = recipeIdFromHash();
  if (recipeId) {
    showRecipe(recipeId);
  } else {
    showCollection();
    loadRecipes();
  }
}

showImportStatus();
updateView();
window.addEventListener('hashchange', updateView);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
}