use std::{
    collections::HashMap,
    path::PathBuf,
    sync::{
        Mutex,
        atomic::{AtomicUsize, Ordering},
    },
};
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

type CachedResult = Result<Option<FileKind>, (io::ErrorKind, String, Option<i32>)>;

/// Cache target observations for one check only. Never normalize paths through symlinks.
pub struct CachedFileSystem<'a> {
    inner: &'a dyn FileSystem,
    enabled: bool,
    entries: Mutex<HashMap<PathBuf, CachedResult>>,
    lookups: AtomicUsize,
    hits: AtomicUsize,
}

impl<'a> CachedFileSystem<'a> {
    pub fn new(inner: &'a dyn FileSystem, enabled: bool) -> Self {
        Self {
            inner,
            enabled,
            entries: Mutex::default(),
            lookups: AtomicUsize::new(0),
            hits: AtomicUsize::new(0),
        }
    }
    pub fn statistics(&self) -> (usize, usize) {
        (
            self.lookups.load(Ordering::Relaxed),
            self.hits.load(Ordering::Relaxed),
        )
    }
}

impl FileSystem for CachedFileSystem<'_> {
    fn kind(&self, path: &Path) -> io::Result<Option<FileKind>> {
        if self.enabled
            && let Some(result) = self
                .entries
                .lock()
                .map_err(|_| io::Error::other("target cache lock poisoned"))?
                .get(path)
                .cloned()
        {
            self.hits.fetch_add(1, Ordering::Relaxed);
            return result.map_err(|(kind, message, code)| match code {
                Some(code) => io::Error::from_raw_os_error(code),
                None => io::Error::new(kind, message),
            });
        }
        self.lookups.fetch_add(1, Ordering::Relaxed);
        let result = self
            .inner
            .kind(path)
            .map_err(|e| (e.kind(), e.to_string(), e.raw_os_error()));
        if self.enabled {
            // Do not hold the lock during I/O. Concurrent misses may perform redundant lookups;
            // the first observation is retained consistently for the remainder of this scan.
            let result = self
                .entries
                .lock()
                .map_err(|_| io::Error::other("target cache lock poisoned"))?
                .entry(path.into())
                .or_insert(result)
                .clone();
            result.map_err(|(kind, message, code)| match code {
                Some(code) => io::Error::from_raw_os_error(code),
                None => io::Error::new(kind, message),
            })
        } else {
            result.map_err(|(kind, message, code)| match code {
                Some(code) => io::Error::from_raw_os_error(code),
                None => io::Error::new(kind, message),
            })
        }
    }
}
