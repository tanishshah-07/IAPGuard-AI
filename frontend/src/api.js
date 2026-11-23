const base=(import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
export async function api(path,options={}){
  const headers=new Headers(options.headers);
  if(options.body != null && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
  let response;
  try { response=await fetch(`${base}/api${path}`,{...options,headers}); }
  catch { throw new Error(`Cannot connect to the API at ${base || 'the local Vite proxy'}.`); }
  const data=await response.json().catch(()=>null);
  if(!response.ok){
    const detail=data?.detail;
    const message=Array.isArray(detail)
      ? detail.map(issue=>`${issue.loc.at(-1)}: ${issue.msg}`).join(' ')
      : detail;
    throw new Error(typeof message==='string'?message:`API request failed (${response.status}).`);
  }
  if(data===null) throw new Error('The API returned an invalid JSON response. Check the API URL or proxy.');
  return data;
}
export const money=(n)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n||0);
export const number=(n)=>new Intl.NumberFormat('en-IN').format(n||0);
export const date=(value)=>new Date(value).toLocaleString('en-IN',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
