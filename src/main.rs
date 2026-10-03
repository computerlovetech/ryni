use ryni::output;

use clap::{Args, Parser, Subcommand, ValueEnum};
use ryni::{
    CheckReport,
    error::ScanError,
    registry::Rule,
    settings::{LintOptions, Overrides, Settings},
};
use std::{
    io::{self, IsTerminal, Write},
    path::PathBuf,
    process::ExitCode,
};

#[derive(Parser)]
#[command(version, about)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Discover supported files and check the selected standards.
    Check(CheckArgs),
    /// Explain one rule, or list all rules when no ID is given.
    Rule { id: Option<String> },
    /// Print resolved settings and pack versions as JSON.
    Settings(CommonArgs),
}

#[derive(Args)]
struct CommonArgs {
    /// Directory or Markdown file to check.
    #[arg(default_value = ".")]
    project: PathBuf,
    /// Configuration path, relative to the working directory.
    #[arg(long, conflicts_with = "isolated")]
    config: Option<PathBuf>,
    /// Ignore configuration files and packs.
    #[arg(long)]
    isolated: bool,
    /// Replace the enabled rule set. Comma-separated IDs or 'all'.
    #[arg(long, value_delimiter = ',')]
    select: Option<Vec<String>>,
    /// Replace ignored rules. Comma-separated IDs or 'all'.
    #[arg(long, value_delimiter = ',')]
    ignore: Option<Vec<String>>,
    /// Allow explicitly selected preview rules.
    #[arg(long)]
    preview: bool,
    /// Replace exclusions with root-relative glob patterns.
    #[arg(long)]
    exclude: Option<Vec<String>>,
    /// Honor ignore files, including .gitignore.
    #[arg(long, conflicts_with = "no_ignore")]
    respect_ignore: bool,
    /// Disable ignore-file filtering.
    #[arg(long)]
    no_ignore: bool,
}

impl CommonArgs {
    fn settings(&self) -> Result<Settings, ScanError> {
        let root = ryni::project_root(&self.project)?;
        Settings::resolve(
            &root,
            self.config.as_deref(),
            self.isolated,
            Overrides {
                lint: LintOptions {
                    select: self.select.clone(),
                    ignore: self.ignore.clone(),
                    preview: self.preview.then_some(true),
                    ..Default::default()
                },
                exclude: self.exclude.clone(),
                respect_ignore: if self.respect_ignore {
                    Some(true)
                } else if self.no_ignore {
                    Some(false)
                } else {
                    None
                },
            },
        )
    }
}

#[derive(Args)]
struct CheckArgs {
    #[command(flatten)]
    common: CommonArgs,
    #[arg(long, value_enum, default_value = "text")]
    output_format: OutputFormat,
    /// Apply safe fixes and recheck. Unsafe fixes require --unsafe-fixes too.
    #[arg(long)]
    fix: bool,
    /// Also apply fixes that may change meaning or remove YAML comments.
    #[arg(long, requires = "fix")]
    unsafe_fixes: bool,
    /// Number of checking threads; discovery remains sequential.
    #[arg(long, default_value_t = 1, value_parser = clap::value_parser!(u16).range(1..=256))]
    threads: u16,
    /// Disable the per-scan target metadata cache.
    #[arg(long)]
    no_cache: bool,
    /// Print phase timings and target lookup counts to stderr.
    #[arg(long)]
    timings: bool,
}

#[derive(Clone, Copy, ValueEnum)]
enum OutputFormat {
    Text,
    Json,
}

fn main() -> ExitCode {
    match execute(Cli::parse()) {
        Ok(code) => ExitCode::from(code),
        Err(error) if error.kind() == io::ErrorKind::BrokenPipe => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::from(2)
        }
    }
}

fn execute(cli: Cli) -> io::Result<u8> {
    let color = io::stdout().is_terminal()
        && std::env::var_os("NO_COLOR").is_none()
        && std::env::var("TERM").as_deref() != Ok("dumb");
    let mut stdout = io::BufWriter::new(io::stdout().lock());
    let code = match cli.command {
        Command::Check(args) => {
            let result = args.common.settings().and_then(|settings| {
                let options = ryni::ExecutionOptions {
                    threads: usize::from(args.threads),
                    cache_targets: !args.no_cache,
                };
                let mut report =
                    ryni::check_with_options(&args.common.project, &settings, options)?;
                if args.fix {
                    let root = ryni::project_root(&args.common.project)?;
                    let applied = ryni::fix::apply(&root, &report, args.unsafe_fixes);
                    if applied.files_changed > 0 {
                        report =
                            ryni::check_with_options(&args.common.project, &settings, options)?;
                    }
                    report.files_fixed = applied.files_changed;
                    report.errors.extend(applied.errors);
                }
                Ok(report)
            });
            let report = result.unwrap_or_else(|error| CheckReport {
                errors: vec![error],
                ..Default::default()
            });
            if args.timings {
                eprintln!("timings: {}", serde_json::to_string(&report.timings)?);
            }
            match args.output_format {
                OutputFormat::Json => {
                    writeln!(stdout, "{}", serde_json::to_string_pretty(&report.json())?)?
                }
                OutputFormat::Text => {
                    if report.files_fixed > 0 {
                        writeln!(stdout, "Fixed {} file(s).", report.files_fixed)?;
                    }
                    for diagnostic in &report.diagnostics {
                        writeln!(stdout, "{}\n", output::render(diagnostic, color))?;
                    }
                    for error in &report.errors {
                        eprintln!("error: {error}");
                    }
                    if !report.diagnostics.is_empty() {
                        let count = report.diagnostics.len();
                        writeln!(
                            stdout,
                            "Found {count} {}.",
                            if count == 1 { "error" } else { "errors" }
                        )?;
                    } else if report.errors.is_empty() {
                        writeln!(
                            stdout,
                            "{}",
                            if report.files_checked == 0 {
                                "No supported files found."
                            } else {
                                "All checks passed!"
                            }
                        )?;
                    }
                }
            }
            report.exit_code()
        }
        Command::Rule { id } => {
            if let Some(id) = id {
                if let Some(rule) = Rule::from_id(&id) {
                    let metadata = rule.metadata();
                    writeln!(
                        stdout,
                        "{} ({:?}, {:?})\n{}",
                        metadata.id, metadata.stability, metadata.scope, metadata.explanation
                    )?;
                    0
                } else {
                    eprintln!("error: unknown rule {id:?}");
                    2
                }
            } else {
                for rule in Rule::ALL {
                    let metadata = rule.metadata();
                    writeln!(
                        stdout,
                        "{}\t{:?}\t{}",
                        rule.id(),
                        metadata.stability,
                        if metadata.default_enabled {
                            "default"
                        } else {
                            "opt-in"
                        }
                    )?;
                }
                0
            }
        }
        Command::Settings(args) => match args.settings() {
            Ok(settings) => {
                writeln!(stdout, "{}", serde_json::to_string_pretty(&settings)?)?;
                0
            }
            Err(error) => {
                eprintln!("error: {error}");
                2
            }
        },
    };
    stdout.flush()?;
    Ok(code)
}
