"""Captura prints da UI do Airflow (localhost:8080) para evidência da entrega."""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/evidencias/prints_airflow")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8080"
USER = "admin"
PASS = "admin_local"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(f"{BASE}/login/", wait_until="domcontentloaded")
        page.wait_for_selector("#username")
        page.screenshot(path=str(OUT / "00_airflow_login.png"), full_page=True)

        page.fill("#username", USER)
        page.fill("#password", PASS)
        page.click('input[type="submit"]')
        page.wait_for_url("**/home**", timeout=60000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "01_airflow_home_dags.png"), full_page=True)

        page.goto(f"{BASE}/dags/citizentech_gtfs_sptrans/grid", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "02_dag_gtfs_grid.png"), full_page=True)

        page.goto(f"{BASE}/dags/citizentech_gtfs_sptrans/graph", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "03_dag_gtfs_graph.png"), full_page=True)

        page.goto(
            f"{BASE}/dags/citizentech_indicadores_reconhecimento/grid",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "04_dag_indicadores_grid.png"), full_page=True)

        page.goto(
            f"{BASE}/dags/citizentech_indicadores_reconhecimento/graph",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "05_dag_indicadores_graph.png"), full_page=True)

        page.goto(
            f"{BASE}/dagrun/list/?_flt_3_dag_id=citizentech_gtfs_sptrans",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "06_dagruns_gtfs.png"), full_page=True)

        page.goto(
            f"{BASE}/dagrun/list/?_flt_3_dag_id=citizentech_indicadores_reconhecimento",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "07_dagruns_indicadores.png"), full_page=True)

        browser.close()

    print("OK prints salvos em", OUT.resolve())
    for f in sorted(OUT.glob("*.png")):
        print(f" - {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
