mod output;

use clap::{Parser, Subcommand};
use std::{io::IsTerminal, path::PathBuf, process::ExitCode};

#[derive(Parser)]
#[command(version, about)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Discover supported files and check them against built-in standards.
    Check {
        /// Directory to scan recursively.
        #[arg(default_value = ".")]
        project: PathBuf,
        /// Disable ignore-file filtering (explicit exclusions still apply).
        #[arg(long)]
        no_ignore: bool,
        /// Exclude a gitignore-style glob relative to the scan root; repeatable.
        #[arg(long, value_name = "GLOB")]
        exclude: Vec<String>,
    },
}

fn main() -> ExitCode {
    match Cli::parse().command {
        Command::Check {
            project,
            no_ignore,
            exclude,
        } => match ryni::check_with_options(&project, &ryni::CheckOptions { no_ignore, exclude }) {
            Ok(report) if report.files_checked == 0 => {
                println!("No supported files found.");
                ExitCode::SUCCESS
            }
            Ok(report) if report.diagnostics.is_empty() => {
                println!("All checks passed!");
                ExitCode::SUCCESS
            }
            Ok(report) => {
                let color = std::io::stdout().is_terminal()
                    && std::env::var_os("NO_COLOR").is_none()
                    && std::env::var("TERM").as_deref() != Ok("dumb");
                for diagnostic in &report.diagnostics {
                    println!("{}\n", output::render(diagnostic, color));
                }
                let count = report.diagnostics.len();
                let noun = if count == 1 { "error" } else { "errors" };
                println!("Found {count} {noun}.");
                ExitCode::from(1)
            }
            Err(error) => {
                eprintln!("error: {error}");
                ExitCode::from(2)
            }
        },
    }
}
