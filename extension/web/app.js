function renderUrlList(id, urls, emptyMessage){
  const list = document.getElementById(id);
  list.replaceChildren();
  if(!urls.length){
    const item = document.createElement('li');
    item.textContent = emptyMessage;
    list.appendChild(item);
    return;
  }
  urls.forEach(url => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = url;
    link.textContent = url;
    item.appendChild(link);
    list.appendChild(item);
  });
}

function slideLabel(currentSlide, slideCount){
  if(!slideCount){
    return 'Slide -- / --';
  }
  return `Slide ${currentSlide + 1} / ${slideCount}`;
}

function renderState(state){
  document.getElementById('status').textContent = state.running ? 'Presentation running' : 'Waiting for slideshow';
  document.getElementById('session').textContent = state.session;
  document.getElementById('slide').textContent = slideLabel(state.currentSlide, state.slideCount);
  document.getElementById('current-title').textContent = state.currentTitle || 'Untitled slide';
  document.getElementById('notes').textContent = state.notes || 'No presenter notes detected.';

  const nextSlide = typeof state.nextSlide === 'number' ? `Slide ${state.nextSlide + 1}` : 'No next slide';
  document.getElementById('next-slide').textContent = nextSlide;
  document.getElementById('next-title').textContent = state.nextTitle || 'No next slide';
  document.getElementById('next-preview').textContent = state.nextPreview || 'The current slide is the last slide in the deck.';

  renderUrlList('local-urls', state.localUrls || [], 'No local URL detected yet.');
  renderUrlList('direct-urls', state.directUrls || [], 'No direct IPv6 address detected.');
}

async function refresh(){
  const response = await fetch('/api/state');
  const state = await response.json();
  renderState(state);
}

async function command(name, payload = {}){
  await fetch('/api/command',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({command:name, ...payload})
  });
  await refresh();
}

document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>command(button.dataset.command)));
document.getElementById('goto-form').addEventListener('submit', async event => {
  event.preventDefault();
  const input = document.getElementById('goto-slide');
  const value = Number.parseInt(input.value, 10);
  if(Number.isNaN(value) || value < 1){
    return;
  }
  await command('goto_slide', {index: value - 1});
});
setInterval(refresh,1500);
refresh().catch(error=>{document.getElementById('status').textContent=String(error);});
