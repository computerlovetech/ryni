use std::{fs, io, path::Path};

/// The environmental dependency of document rules. Tests and editors can supply their own view.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileKind {
    File,
    Directory,
    Other,
}

pub trait FileSystem: Sync {
    fn kind(&self, path: &Path) -> io::Result<Option<FileKind>>;
    fn exists(&self, path: &Path) -> io::Result<bool> {
        self.kind(path).map(|kind| kind.is_some())
    }
    fn is_file(&self, path: &Path) -> io::Result<bool> {
        self.kind(path).map(|kind| kind == Some(FileKind::File))
    }
}

pub struct OsFileSystem;

impl FileSystem for OsFileSystem {
    fn kind(&self, path: &Path) -> io::Result<Option<FileKind>> {
        match fs::metadata(path) {
            Ok(metadata) => Ok(Some(if metadata.is_file() {
                FileKind::File
            } else if metadata.is_dir() {
                FileKind::Directory
            } else {
                FileKind::Other
            })),
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                ) =>
            {
                Ok(None)
            }
            Err(error) => Err(error),
        }
    }
}
