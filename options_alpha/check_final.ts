async function check() {
  const url = 'http://127.0.0.1:5000/health';
  console.log(`Checking ${url}...`);
  try {
    const res = await fetch(url);
    console.log(`Status: ${res.status}`);
  } catch (e: any) {
    console.error(`Error: ${e.message}`);
  }
}
check();
