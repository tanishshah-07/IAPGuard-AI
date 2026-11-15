const base=import.meta.env.VITE_API_URL || '';
export async function api(path,options={}){
  let response;
  try { response=await fetch(`${base}/api${path}`,{headers:{'Content-Type':'application/json'},...options}); }
  catch { throw new Error('Cannot connect to the API. Start the backend on port 8000.'); }
  const data=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status})`);
  return data;
}
export const money=(n)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n||0);
export const number=(n)=>new Intl.NumberFormat('en-IN').format(n||0);
export const date=(value)=>new Date(value).toLocaleString('en-IN',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
