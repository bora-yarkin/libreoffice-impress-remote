async function refresh(){
  const response = await fetch('/api/state');
  const state = await response.json();
  document.getElementById('status').textContent = state.running ? 'Running' : 'Stopped';
  document.getElementById('slide').textContent = `Slide ${state.currentSlide + 1} / ${state.slideCount}`;
  document.getElementById('notes').textContent = state.notes || 'No presenter notes detected.';
}
async function command(name){
  await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:name})});
  await refresh();
}
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>command(button.dataset.command)));
setInterval(refresh,1500);
refresh().catch(error=>{document.getElementById('status').textContent=String(error);});
