use clap::{Parser, Subcommand};
use std::{path::PathBuf, process::ExitCode};

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
    },
}

fn main() -> ExitCode {
    match Cli::parse().command {
        Command::Check { project } => match ryni::check(&project) {
            Ok(report) if report.files_checked == 0 => {
                println!("No supported files found.");
                ExitCode::SUCCESS
            }
            Ok(report) if report.diagnostics.is_empty() => {
                println!("All checks passed!");
                ExitCode::SUCCESS
            }
            Ok(report) => {
                for diagnostic in &report.diagnostics {
                    println!(
                        "{}: {} {}",
                        diagnostic.path.display(),
                        diagnostic.rule,
                        diagnostic.message
                    );
                }
                println!("\nFound {} violation(s).", report.diagnostics.len());
                ExitCode::from(1)
            }
            Err(error) => {
                eprintln!("error: {error}");
                ExitCode::from(2)
            }
        },
    }
}
