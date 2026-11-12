from pathlib import Path

from nicegui import app


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


APP_CSS = """
<style>
  :root {
    --piec-primary: #5f489d;
    --piec-header: #3e0565;
    --piec-text: rgba(30, 30, 30, 0.8);
    --piec-muted: rgba(109, 110, 113, 0.5);
    --piec-line: rgba(95, 72, 157, 0.45);
  }
  @layer overrides {
    .workflow-root .workflow-step-status.disabled { opacity: 1 !important; }
    .workflow-root .workflow-next.disabled, .workflow-root .workflow-command.disabled {
      background: #888888 !important;
      color: #ffffff !important;
      opacity: 1 !important;
    }
  }
  body { background: #eeeeee; color: var(--piec-text); font-family: "UFES Sans", sans-serif; letter-spacing: 0; }
  .nicegui-content { max-width: none; width: 100%; padding: 0; margin: 0; gap: 0; }
  .q-btn { font-family: inherit; letter-spacing: 0; text-transform: none; }
  .q-card { box-shadow: none; border-radius: 12px; }
  .q-field__label { font-weight: 400; }
  .q-field__native::placeholder { color: var(--piec-muted); opacity: 1; }
  .workflow-root { width: 100%; min-height: 100vh; }
  .workflow-header { height: 72px; background: var(--piec-header); color: #ffffff; }
  .workflow-header-inner { max-width: 1296px; height: 100%; margin: auto; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
  .workflow-wordmark { display: flex; align-items: center; gap: 12px; }
  .workflow-wordmark-name { font-size: 30px; line-height: 34px; font-weight: 700; white-space: nowrap; }
  .workflow-wordmark-description { font-size: 11px; line-height: 13px; }
  .workflow-user { display: flex; align-items: center; gap: 9px; font-size: 16px; font-weight: 700; }
  .workflow-avatar { width: 30px; height: 30px; border-radius: 50%; background: #d9d9d9; color: var(--piec-header); font-size: 20px; display: grid; place-items: center; }
  .workflow-root .workflow-folder-button { margin-left: 12px; color: #ffffff; }
  .workflow-progress { background: #d9d9d9; min-height: 115px; padding: 28px 24px 24px; }
  .workflow-steps { max-width: 1484px; margin: auto; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); position: relative; }
  .workflow-steps::before { content: ''; position: absolute; height: 1px; top: 14px; left: 16.667%; right: 16.667%; background: var(--piec-primary); }
  .workflow-step { display: flex; align-items: center; flex-direction: column; gap: 10px; min-width: 0; }
  .workflow-step .workflow-step-status { width: 184px; min-height: 29px; padding: 0 10px; border: 1px solid var(--piec-primary); border-radius: 8px; background: #d9d9d9; color: var(--piec-text); font-size: 16px; line-height: 22px; }
  .workflow-step.complete .workflow-step-status { background: var(--piec-primary); color: #ffffff; }
  .workflow-step-title { font-size: 20px; line-height: 24px; font-weight: 700; text-align: center; }
  .workflow-main { max-width: 1338px; width: calc(100% - 64px); margin: auto; padding: 28px 0 70px; }
  .workflow-heading { margin: 0; padding: 0 0 8px; border-bottom: 1px solid var(--piec-primary); color: var(--piec-primary); font-size: 30px; line-height: 36px; font-weight: 700; }
  .workflow-description { margin-top: 14px; font-size: 20px; line-height: 26px; }
  .workflow-description-gap { height: 40px; }
  .workflow-page { width: 100%; }
  .workflow-root .workflow-panel { margin: 44px 38px 0; width: calc(100% - 76px); padding: 32px 62px; border-radius: 30px; background: #ffffff; color: var(--piec-text); display: flex; flex-direction: column; gap: 0; min-width: 0; }
  .workflow-panel-title { font-size: 24px; line-height: 30px; font-weight: 700; color: var(--piec-primary); }
  .workflow-panel-description { font-size: 20px; line-height: 26px; margin-top: 8px; }
  .workflow-tool-row { display: flex; justify-content: space-between; align-items: center; gap: 32px; width: 100%; }
  .workflow-tool-copy { min-width: 0; }
  .workflow-root .workflow-command { min-height: 64px; padding: 12px 30px; border-radius: 11px; font-size: 24px; line-height: 30px; font-weight: 700; flex-shrink: 0; }
  .workflow-root .workflow-command.q-btn--outline { border-radius: 11px; }
  .workflow-root .workflow-panel-footer { width: 100%; border-top: 1px solid var(--piec-line); padding-top: 10px; margin-top: 43px; font-size: 18px; line-height: 24px; white-space: pre-wrap; overflow-wrap: anywhere; }
  .workflow-root .workflow-workdir { margin-top: 76px; min-height: 468px; padding: 99px 64px; }
  .workflow-workdir-path { width: 100%; margin-top: 32px; font-size: 20px; line-height: 26px; overflow-wrap: anywhere; }
  .workflow-root .workflow-workdir .workflow-panel-footer { margin-top: 86px; padding-top: 16px; }
  .workflow-root .workflow-parameters { min-height: 235px; }
  .workflow-root .workflow-processing { margin-top: 28px; }
  .workflow-processing-controls { display: flex; align-items: center; width: 100%; gap: 38px; margin-top: 26px; }
  .workflow-processing-controls .workflow-field { flex: 1; min-width: 0; }
  .workflow-field .q-field__control { min-height: 48px; border-radius: 10px; }
  .workflow-field .q-field__control:before { border-color: var(--piec-primary); }
  .workflow-field .q-field__control:after { height: 100%; }
  .workflow-field .q-field__native { font-size: 20px; color: var(--piec-text); }
  .workflow-root .workflow-config { margin-top: 90px; padding: 36px 44px 32px; }
  .workflow-config-fields { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 24px 28px; width: 100%; margin-top: 60px; }
  .workflow-config-fields .q-field__control { min-height: 69px; }
  .workflow-config-fields .q-field__label { font-size: 15px; }
  .workflow-config-fields .q-field__native { font-size: 20px; }
  .workflow-config-save { display: flex; width: 100%; justify-content: flex-end; margin-top: 44px; }
  .workflow-footer { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin: 72px 38px 0; }
  .workflow-footer-actions { display: flex; justify-content: flex-end; align-items: center; gap: 20px; flex-wrap: wrap; margin-left: auto; }
  .workflow-root .workflow-next { border-radius: 36px; min-width: 294px; min-height: 67px; padding: 14px 30px; font-size: 28px; line-height: 34px; font-weight: 700; }
  .workflow-back { font-size: 20px; }
  .workflow-review-toolbar { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin: 24px 38px 0; flex-wrap: wrap; }
  .workflow-review-toolbar .q-btn { font-size: 17px; }
  .workflow-review-area { width: 100%; }
  .workflow-review-placeholder { margin: 44px 38px 0; padding: 50px 62px; border: 1px solid var(--piec-line); border-radius: 12px; background: #ffffff; font-size: 20px; }
  .review-summary { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 22px; margin: 34px 38px; }
  .review-stat { border: 1px solid var(--piec-primary); border-radius: 9px; padding: 14px 18px; background: #ffffff; min-height: 94px; min-width: 0; }
  .review-stat-title { font-size: 15px; line-height: 20px; }
  .review-stat-value { font-size: 28px; line-height: 34px; font-weight: 700; color: var(--piec-primary); }
  .workflow-root .review-pair { margin: 34px 38px 0; width: calc(100% - 76px); padding: 36px; border-radius: 26px; gap: 18px; }
  .review-pair-navigation { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 20px; width: 100%; }
  .review-pair-title { font-size: 16px; line-height: 22px; text-align: center; font-weight: 700; }
  .review-pair-metadata { font-size: 15px; line-height: 22px; overflow-wrap: anywhere; }
  .review-records { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; width: 100%; }
  .review-record { width: 100%; min-width: 0; gap: 12px; }
  .review-record-title { font-size: 17px; font-weight: 700; }
  .review-table { width: 100%; max-height: 420px; overflow-y: auto; border: 1px solid #dddddd; border-radius: 8px; }
  .review-table .q-table th { font-weight: 700; }
  .review-table .q-table td { white-space: normal; overflow-wrap: anywhere; }
  .review-table .q-table th:first-child, .review-table .q-table td:first-child { width: 42%; }
  .review-table .q-table { table-layout: fixed; }
  .review-notes { width: 100%; margin-top: 10px; }
  .review-actions { display: flex; justify-content: flex-end; gap: 20px; width: 100%; margin-top: 24px; flex-wrap: wrap; }
  .review-actions .q-btn { min-height: 58px; padding: 10px 26px; font-size: 22px; font-weight: 700; border-radius: 14px; }
  .workflow-download-key { width: calc(100% - 40px); max-width: 620px; margin: 0 20px; flex-shrink: 0; }
  .workflow-downloads { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; margin: 0 20px; flex: 1; min-height: 220px; }
  .workflow-root .workflow-download-card { width: 100%; min-width: 0; padding: 32px 24px; gap: 28px; border-radius: 24px; align-items: center; justify-content: center; background: #ffffff; }
  .workflow-download-card .workflow-panel-title { text-align: center; }
  .workflow-root .workflow-download-card .workflow-command { max-width: 100%; white-space: normal; }
  .q-dialog .q-card { max-width: calc(100vw - 32px); }
  @media (max-width: 1400px) {
    .workflow-header-inner { margin: 0 32px; }
    .workflow-root .workflow-panel { margin-left: 20px; margin-right: 20px; width: calc(100% - 40px); padding: 32px; }
    .workflow-root .workflow-workdir { padding: 70px 48px; }
    .workflow-footer { margin-left: 20px; margin-right: 20px; }
    .workflow-config-fields { gap: 24px 18px; }
    .workflow-config-fields .q-field__label { font-size: 13px; }
    .review-summary { margin-left: 20px; margin-right: 20px; gap: 14px; }
    .workflow-root .review-pair { margin-left: 20px; margin-right: 20px; width: calc(100% - 40px); }
  }
  @media (max-width: 1000px) {
    .workflow-downloads { margin-top: 28px; }
    .workflow-download-key { margin-top: 28px; }
    .workflow-root .workflow-download-card { min-height: 240px; }
    .workflow-config-fields { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 36px; }
    .workflow-config-fields .q-field__label { font-size: 14px; }
    .workflow-root .workflow-config { margin-top: 44px; }
    .review-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .workflow-tool-row { align-items: flex-start; }
    .workflow-root .workflow-command { font-size: 20px; padding: 10px 20px; min-height: 56px; }
    .workflow-processing-controls { flex-wrap: wrap; gap: 20px; }
    .workflow-processing-controls .workflow-field { flex-basis: 100%; }
    .workflow-root .workflow-next { min-width: 200px; font-size: 22px; }
  }
  @media (max-width: 650px) {
    .workflow-downloads { grid-template-columns: minmax(0, 1fr); margin: 24px 0 0; gap: 20px; }
    .workflow-download-key { width: 100%; margin: 24px 0 0; }
    .workflow-root .workflow-download-card { border-radius: 20px; }
    .workflow-header { height: auto; min-height: 72px; }
    .workflow-header-inner { margin: 0; padding: 16px 20px; gap: 16px; flex-wrap: wrap; }
    .workflow-wordmark-name { font-size: 25px; }
    .workflow-wordmark-description { font-size: 10px; }
    .workflow-user { font-size: 14px; }
    .workflow-progress { min-height: 96px; padding: 20px 12px; }
    .workflow-step .workflow-step-status { width: calc(100% - 12px); min-width: 0; font-size: 13px; padding: 0 4px; }
    .workflow-step-title { font-size: 13px; line-height: 17px; overflow-wrap: anywhere; }
    .workflow-main { width: calc(100% - 32px); padding-top: 24px; }
    .workflow-heading { font-size: 26px; line-height: 32px; }
    .workflow-description { font-size: 18px; line-height: 24px; }
    .workflow-root .workflow-panel, .workflow-root .review-pair { width: 100%; margin: 30px 0 0; padding: 24px; border-radius: 20px; }
    .workflow-root .workflow-workdir { min-height: 360px; padding: 36px 24px; }
    .workflow-root .workflow-workdir .workflow-panel-footer { margin-top: 50px; }
    .workflow-root .workflow-parameters { min-height: 0; }
    .workflow-tool-row { flex-direction: column; gap: 24px; }
    .workflow-root .workflow-command { width: 100%; font-size: 19px; line-height: 26px; white-space: normal; }
    .workflow-panel-title { font-size: 23px; line-height: 28px; }
    .workflow-panel-description, .workflow-workdir-path { font-size: 18px; line-height: 24px; }
    .workflow-config-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px 14px; }
    .workflow-config-fields .q-field__label { font-size: 13px; }
    .workflow-config-fields .q-field__control { padding: 0 8px; }
    .workflow-config-save { margin-top: 30px; }
    .workflow-footer { margin: 32px 0 0; align-items: stretch; flex-direction: column; gap: 12px; }
    .workflow-footer-actions { flex-direction: column; gap: 12px; }
    .workflow-footer-actions { margin-left: 0; width: 100%; }
    .workflow-root .workflow-next { width: 100%; min-width: 0; min-height: 58px; font-size: 22px; }
    .workflow-back { align-self: flex-start; }
    .workflow-review-toolbar { margin: 22px 0 0; justify-content: flex-start; }
    .workflow-review-placeholder { margin: 30px 0 0; padding: 28px 24px; }
    .review-summary { margin: 24px 0; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .review-stat { padding: 12px; }
    .review-records { grid-template-columns: minmax(0, 1fr); }
    .review-pair-navigation { gap: 10px; }
    .review-pair-title { font-size: 13px; line-height: 18px; }
    .review-pair-navigation .q-btn { padding: 4px 8px; }
    .review-actions { gap: 12px; margin-top: 10px; }
    .review-actions .q-btn { width: 100%; }
    .workflow-field .q-field__native { font-size: 17px; }
  }
  @media (max-width: 360px) {
    .workflow-step-title { font-size: 12px; line-height: 16px; }
  }
  @media (min-width: 1001px) {
    .workflow-root { height: 100dvh; min-height: 0; display: flex; flex-direction: column; }
    .workflow-header { height: 60px; flex: 0 0 60px; }
    .workflow-progress { min-height: 84px; flex: 0 0 84px; padding: 14px 24px 10px; }
    .workflow-step { gap: 8px; }
    .workflow-step-title { font-size: 18px; line-height: 22px; }
    .workflow-main { flex: 1; min-height: 0; margin: 0 auto; padding: 18px 0 16px; display: flex; flex-direction: column; }
    .workflow-page { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 14px; }
    .workflow-heading { flex-shrink: 0; font-size: 28px; line-height: 34px; padding-bottom: 6px; }
    .workflow-description { flex-shrink: 0; margin: 0; line-height: 24px; }
    .workflow-description-gap { display: none; }
    .workflow-root .workflow-panel { width: calc(100% - 40px); margin: 0 20px; padding: 20px 32px; min-height: 0; border-radius: 24px; }
    .workflow-panel-description { font-size: 18px; line-height: 24px; margin-top: 4px; }
    .workflow-root .workflow-command { min-height: 46px; padding: 8px 22px; font-size: 20px; line-height: 26px; }
    .workflow-root .workflow-panel-footer { margin-top: 18px; padding-top: 10px; font-size: 17px; line-height: 22px; }
    .workflow-root .workflow-workdir { flex: 1; justify-content: center; padding: 24px 40px; }
    .workflow-workdir-path { margin-top: 20px; font-size: 18px; line-height: 24px; }
    .workflow-root .workflow-workdir .workflow-panel-footer { margin-top: 28px; padding-top: 12px; }
    .workflow-parameters .workflow-panel-footer:empty { display: none; }
    .workflow-processing-controls { margin-top: 16px; gap: 24px; }
    .workflow-root .workflow-config { padding: 24px 32px; }
    .workflow-config-fields { margin-top: 24px; gap: 18px 24px; }
    .workflow-config-fields .q-field__control { min-height: 58px; }
    .workflow-config-save { margin-top: 20px; }
    .workflow-footer { flex-shrink: 0; min-height: 48px; margin: 16px 20px 0; gap: 16px; }
    .workflow-root .workflow-next { min-height: 48px; min-width: 220px; padding: 8px 24px; border-radius: 26px; font-size: 22px; line-height: 28px; }
    .workflow-footer-actions { gap: 16px; }
    .workflow-review-toolbar { flex-shrink: 0; margin: 0 20px; gap: 12px; }
    .workflow-review-toolbar .q-btn { min-height: 34px; font-size: 15px; }
    .workflow-review-area { flex: 1; min-height: 0; align-items: stretch; gap: 12px; }
    .workflow-review-placeholder { margin: 0 20px; padding: 28px 32px; }
    .review-summary { flex-shrink: 0; margin: 0 20px; gap: 14px; }
    .review-stat { min-height: 64px; padding: 8px 12px; }
    .review-stat-title { font-size: 13px; line-height: 16px; }
    .review-stat-value { font-size: 24px; line-height: 28px; }
    .workflow-root .review-pair { flex: 1; min-height: 0; margin: 0 20px; width: calc(100% - 40px); padding: 16px 20px; gap: 10px; }
    .review-pair-navigation { flex-shrink: 0; gap: 12px; }
    .review-pair-navigation .q-btn { min-height: 32px; padding: 4px 10px; font-size: 14px; }
    .review-pair-title { font-size: 14px; line-height: 18px; }
    .review-pair-metadata { flex-shrink: 0; font-size: 13px; line-height: 18px; }
    .review-records { flex: 1; min-height: 0; gap: 16px; grid-template-rows: minmax(0, 1fr); align-self: stretch; }
    .review-record { height: 100%; min-height: 0; gap: 6px; }
    .review-record-title { flex-shrink: 0; font-size: 16px; line-height: 22px; }
    .review-table { flex: 1; min-height: 0; max-height: none; }
    .review-table .q-table__container { height: 100%; min-height: 0; }
    .review-table .q-table__middle { flex: 1; min-height: 0; overflow: auto; }
    .review-table .q-table__bottom { flex-shrink: 0; min-height: 32px; padding: 4px 8px; }
    .review-table .q-table__bottom .q-field__control,
    .review-table .q-table__bottom .q-field__marginal { height: 24px; min-height: 24px; }
    .review-table .q-table__bottom .q-field__native { min-height: 24px; padding: 0; }
    .review-table .q-table__bottom .q-btn { min-height: 24px; padding: 2px 6px; }
    .review-table .q-table thead tr, .review-table .q-table th { height: 32px; }
    .review-table .q-table th, .review-table .q-table td { padding: 6px 12px; }
    .review-table .q-table tbody td { height: 32px; }
    .review-notes { flex-shrink: 0; margin: 0; }
    .review-notes .q-field__control { height: 56px; min-height: 56px; }
    .review-notes .q-field__native { font-size: 16px; max-height: 48px; overflow-y: auto !important; }
    .review-actions { flex-shrink: 0; margin: 0; gap: 12px; }
    .review-actions .q-btn { min-height: 42px; padding: 6px 20px; font-size: 18px; }
  }
  @media (min-width: 1001px) and (max-height: 800px) {
    .workflow-header { height: 56px; flex-basis: 56px; }
    .workflow-progress { min-height: 76px; flex-basis: 76px; padding: 10px 24px 8px; }
    .workflow-step { gap: 6px; }
    .workflow-main { padding: 12px 0; }
    .workflow-page { gap: 10px; }
    .workflow-heading { font-size: 26px; line-height: 32px; padding-bottom: 4px; }
    .workflow-root .workflow-panel { padding: 16px 24px; }
    .workflow-panel-title { font-size: 22px; line-height: 26px; }
    .workflow-panel-description { font-size: 17px; line-height: 22px; }
    .workflow-root .workflow-panel-footer { margin-top: 12px; padding-top: 8px; font-size: 16px; line-height: 22px; }
    .workflow-processing-controls { margin-top: 12px; }
    .workflow-config-fields { margin-top: 18px; gap: 14px 24px; }
    .workflow-config-save { margin-top: 16px; }
    .workflow-footer { margin-top: 10px; min-height: 46px; }
    .workflow-root .workflow-next { min-height: 46px; }
    .workflow-review-area { gap: 8px; }
    .review-stat { min-height: 58px; padding: 6px 12px; }
    .workflow-root .review-pair {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-rows: auto auto minmax(0, 1fr) auto;
      grid-template-areas: "navigation navigation" "metadata metadata" "records records" "notes actions";
      padding: 12px 16px;
      gap: 8px;
    }
    .review-pair-navigation { grid-area: navigation; }
    .review-pair-metadata { grid-area: metadata; }
    .review-records { grid-area: records; }
    .review-notes { grid-area: notes; }
    .review-actions { grid-area: actions; width: auto; align-items: center; }
    .review-notes .q-field__control { height: 50px; min-height: 50px; }
    .review-notes .q-field__native { max-height: 42px; }
    .review-actions .q-btn { min-height: 40px; }
  }
  @media (min-width: 1001px) and (max-height: 650px) {
    .workflow-header { height: 48px; flex-basis: 48px; }
    .workflow-progress { min-height: 64px; flex-basis: 64px; padding: 6px 24px; }
    .workflow-step { gap: 4px; }
    .workflow-step-title { font-size: 16px; line-height: 18px; }
    .workflow-main { padding: 8px 0; }
    .workflow-page { gap: 8px; }
    .workflow-footer { margin-top: 8px; min-height: 42px; }
    .workflow-root .workflow-command, .workflow-root .workflow-next { min-height: 42px; padding: 6px 20px; }
    .workflow-review-toolbar .q-btn { min-height: 30px; }
    .review-stat { min-height: 48px; padding: 4px 12px; }
    .review-stat-value { font-size: 22px; line-height: 24px; }
    .workflow-review-area { gap: 6px; }
    .workflow-root .review-pair { padding: 10px 14px; gap: 6px; }
    .review-notes .q-field__control { height: 44px; min-height: 44px; }
    .review-notes .q-field__native { max-height: 38px; }
    .review-actions .q-btn { min-height: 36px; padding: 4px 16px; }
  }
</style>
"""
