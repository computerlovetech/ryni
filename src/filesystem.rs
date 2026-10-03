use std::{fs, io, path::Path};

/// The environmental dependency of document rules. Tests and editors can supply their own view.
pub trait FileSystem: Sync {
    fn exists(&self, path: &Path) -> io::Result<bool>;
}

pub struct OsFileSystem;

impl FileSystem for OsFileSystem {
    fn exists(&self, path: &Path) -> io::Result<bool> {
        match fs::metadata(path) {
            Ok(_) => Ok(true),
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                ) =>
            {
                Ok(false)
            }
            Err(error) => Err(error),
        }
    }
}
