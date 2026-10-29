from pathlib import Path

from nicegui import app, ui


ASSETS_DIR = Path(__file__).parent / "assets"
FONTE_REGULAR_URL = app.add_static_file(local_file=ASSETS_DIR / "UfesSans-Regular.ttf")
FONTE_BOLD_URL = app.add_static_file(local_file=ASSETS_DIR / "UfesSans-Bold.ttf")
FONTES_CSS = f"""
<style>
  @font-face {{
    font-family: "UFES Sans";
    src: url("{FONTE_REGULAR_URL}") format("truetype");
    font-weight: 400;
    font-style: normal;
    font-display: swap;
  }}
  @font-face {{
    font-family: "UFES Sans";
    src: url("{FONTE_BOLD_URL}") format("truetype");
    font-weight: 700;
    font-style: normal;
    font-display: swap;
  }}
</style>
"""


LOGIN_CSS = """
<style>
  .login-dialog .q-dialog__inner { padding: 0; }
  .login-screen {
    --login-primary: #5f489d;
    --login-placeholder: rgba(109, 110, 113, 0.5);
    --login-text: rgba(30, 30, 30, 0.8);
    --login-footer: #3e0565;
    --q-primary: var(--login-primary);
    width: 100%;
    height: 100%;
    max-width: none !important;
    max-height: none !important;
    border-radius: 0 !important;
    display: flex;
    flex-direction: column;
    color: #ffffff;
    font-family: "UFES Sans", sans-serif;
    letter-spacing: 0;
    background: linear-gradient(125deg, #6a5ca8 0%, #5c51a2 26.2%, #52499e 36.9%, #474099 50%, #3c3393 63.1%, #2f2f88 73.8%, #27266b 100%);
  }
  .login-main {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 32px;
  }
  .login-content {
    width: 1064px;
    max-width: 100%;
    display: grid;
    grid-template-columns: minmax(0, 334px) 508px;
    column-gap: 208px;
    align-items: center;
    transform: translateY(8px);
  }
  .login-brand {
    position: relative;
    width: 321px;
    max-width: 100%;
    aspect-ratio: 321 / 269;
    overflow: hidden;
    transform: translate(4px, -23.5px);
  }
  .login-brand .login-brand-logo {
    position: absolute;
    left: calc(-100% * 106 / 321);
    top: calc(-100% * 45 / 269);
    width: calc(100% * 495 / 321);
    height: calc(100% * 361 / 269);
    max-width: none;
  }
  .login-screen .login-card {
    width: 508px;
    max-width: 100%;
    min-width: 0;
    height: 468px;
    padding: 49px 58px 31px;
    display: flex;
    flex-direction: column;
    gap: 0;
    background: #ffffff;
    color: var(--login-text);
    border-radius: 33px;
    box-shadow: none;
  }
  .login-title {
    margin: 0;
    font-size: 36px;
    line-height: 46px;
    font-weight: 700;
    color: var(--login-primary);
  }
  .login-description { margin: 9px 0 46px; font-size: 15.5px; line-height: 20px; white-space: nowrap; }
  .login-field { width: 100%; padding: 0; }
  .login-field + .login-field { margin-top: 38px; }
  .login-field .q-field__control {
    height: 69px;
    min-height: 69px;
    padding: 0 18px;
    border-radius: 15px;
    color: var(--login-primary);
  }
  .login-field .q-field__control:before,
  .login-field .q-field__control:hover:before { border: 1px solid var(--login-primary); }
  .login-field .q-field__control:after { border-width: 1px; }
  .login-field .q-field__native { padding: 0; font-size: 20px; color: var(--login-text); }
  .login-field .q-field__native::placeholder { color: var(--login-placeholder); opacity: 1; }
  .login-field .q-field__label {
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  .login-field .q-field__append { height: 69px; opacity: 0; }
  .login-field:hover .q-field__append,
  .login-field:focus-within .q-field__append { opacity: 1; }
  .login-error {
    width: 100%;
    min-height: 20px;
    flex-shrink: 0;
    margin-top: 9px;
    color: #ff3333;
    font-size: 16px;
    line-height: 20px;
  }
  .login-screen .login-submit {
    align-self: center;
    flex-shrink: 0;
    width: 242px;
    min-height: 48px;
    margin-top: 14px;
    padding: 0 20px;
    border-radius: 24px;
    background: var(--login-primary);
    color: #ffffff;
    font-family: inherit;
    font-size: 24px;
    line-height: 28px;
    font-weight: 700;
    letter-spacing: 0;
  }
  .login-footer {
    flex: 0 0 107px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--login-footer);
  }
  .login-footer-logo { width: 394px; height: 90px; max-width: calc(100% - 32px); object-fit: contain; }
  @media (max-width: 1150px) {
    .login-content { width: 950px; grid-template-columns: minmax(0, 1fr) 508px; column-gap: 64px; }
  }
  @media (max-width: 850px) {
    .login-main { padding: 40px 24px; }
    .login-content { width: 508px; grid-template-columns: minmax(0, 1fr); gap: 36px; transform: none; }
    .login-brand { width: 222px; transform: none; }
    .login-footer { flex-basis: 90px; }
  }
  @media (max-width: 560px) {
    .login-main { padding: 32px 20px; }
    .login-screen .login-card { width: 100%; height: auto; padding: 32px 24px; border-radius: 26px; }
    .login-title { font-size: 32px; line-height: 38px; }
    .login-description { margin: 10px 0 30px; white-space: normal; font-size: 17px; line-height: 22px; }
    .login-field .q-field__control, .login-field .q-field__append { height: 60px; min-height: 60px; }
    .login-field + .login-field { margin-top: 24px; }
    .login-error { margin-top: 6px; min-height: 18px; line-height: 18px; }
    .login-screen .login-submit { width: 100%; max-width: 242px; margin-top: 6px; }
  }
</style>
"""


def montar_login(autenticar_usuario):
    ui.add_head_html(FONTES_CSS)
    ui.add_head_html(LOGIN_CSS)
    dialog = ui.dialog().props("persistent maximized").classes("login-dialog")
    with dialog, ui.element("div").classes("login-screen"):
        with ui.element("main").classes("login-main"):
            with ui.element("div").classes("login-content"):
                with ui.element("section").classes("login-brand").props('aria-label="integra FISCAL"'):
                    ui.image(ASSETS_DIR / "nome_solucao.png").props(
                        'fit=contain no-spinner alt="integra FISCAL. Inteligência cadastral para a gestão fiscal"'
                    ).classes("login-brand-logo")
                with ui.card().classes("login-card"):
                    ui.label("Registro de acesso").classes("login-title")
                    ui.label("Informe seu nome e senha padrão para realizar o registro.").classes("login-description")
                    nome = ui.input("Nome do usuário", placeholder="Nome do usuário").props(
                        'outlined stack-label hide-bottom-space aria-label="Nome do usuário"'
                    ).classes("login-field")
                    senha = ui.input("Senha", placeholder="Senha", password=True, password_toggle_button=True).props(
                        'outlined stack-label hide-bottom-space aria-label="Senha"'
                    ).classes("login-field")
                    erro = ui.label("").props('role=alert aria-live=polite aria-atomic=true').classes("login-error")
                    ui.button("Registrar", on_click=autenticar_usuario, color=None).props("unelevated no-caps").classes("login-submit")
        with ui.element("footer").classes("login-footer"):
            logo = ASSETS_DIR / "labcidades.png"
            ui.image(logo).props(
                'fit=contain no-spinner alt="desenvolvido por LabCidades, Laboratório de Projetos"'
            ).classes("login-footer-logo")
    return dialog, nome, senha, erro
