import { execa } from 'execa';
import { publicIpv4 } from 'public-ip';
import chalk from 'chalk';

async function startFrontend() {
  const port = 3000;

  console.log(chalk.cyan('Starting frontend server...'));

  // Launch the 'serve' server in the background
  const serveProcess = execa('serve', ['-s', 'build', '-l', port]);

  // Pipe server logs to the console in real-time
  serveProcess.stderr?.pipe(process.stderr);
  serveProcess.stdout?.pipe(process.stdout);

  // Wait for the server to be ready
  try {
    await new Promise(resolve => setTimeout(resolve, 1500)); // Short delay to let serve start

    const ip = await publicIpv4({ timeout: 2000 });

    console.log(chalk.green('\n----------------------------------------------------'));
    console.log(chalk.green.bold('✅ Frontend is ready!'));
    console.log(`\n- ${chalk.bold('Local:')}    http://localhost:${port}`);
    console.log(`- ${chalk.bold('Public:')}   http://${ip}:${port} (if port 3000 is open)`);
    console.log(chalk.green('----------------------------------------------------\n'));
  } catch (error) {
    console.log(chalk.yellow('\nCould not determine public IP. You can still access the frontend via localhost or your server\'s public IP if you know it.'));
  }
}

startFrontend();