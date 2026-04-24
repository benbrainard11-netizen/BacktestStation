use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::{Manager, RunEvent};

struct SidecarHandle(Mutex<Option<Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .manage(SidecarHandle(Mutex::new(None)))
        .setup(|app| {
            match spawn_backend() {
                Ok(child) => {
                    if let Some(state) = app.try_state::<SidecarHandle>() {
                        *state.0.lock().expect("sidecar mutex poisoned") = Some(child);
                    }
                    println!("[sidecar] uvicorn launched on :8000");
                }
                Err(err) => {
                    eprintln!(
                        "[sidecar] failed to start backend ({err}); the UI will show API OFFLINE until uvicorn is started manually"
                    );
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<SidecarHandle>() {
                if let Some(mut child) = state
                    .0
                    .lock()
                    .expect("sidecar mutex poisoned")
                    .take()
                {
                    let _ = child.kill();
                }
            }
        }
    });
}

/// Best-effort: launch `python -m uvicorn app.main:app --port 8000`
/// from the repo's `backend/` directory.
///
/// Path resolution assumes `npm run tauri dev` — i.e. cwd is
/// `frontend/src-tauri`. Packaged release builds need a different
/// strategy (bundled Python interpreter or compiled sidecar binary);
/// that's a TODO once Phase 1 is wired.
fn spawn_backend() -> std::io::Result<Child> {
    let cwd = std::env::current_dir()?;
    let backend_dir = cwd.join("..").join("..").join("backend");

    if !backend_dir.exists() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("backend dir not found at {}", backend_dir.display()),
        ));
    }

    Command::new("python")
        .args(["-m", "uvicorn", "app.main:app", "--port", "8000"])
        .current_dir(&backend_dir)
        .spawn()
}
