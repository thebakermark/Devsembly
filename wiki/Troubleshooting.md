# Troubleshooting

## Browser IDE does not load

1. Check DNS resolution.
2. Check reverse-proxy and code-server containers.
3. Check firewall rules.
4. Use the Vultr web console for emergency access.
5. Review service logs and certificate status.

## Agent task is stuck

1. Check the task's worktree and process status.
2. Check model API authentication and limits.
3. Review the Archon step currently running.
4. Stop repeated retry loops.
5. Escalate with the issue, logs, and partial work preserved.

## GitHub push fails

Check the repository remote, authentication, branch name, permissions, and whether the GitHub App is installed for that repository.

## Coolify deployment fails

Review build logs, required environment variables, Docker health checks, database migrations, disk space, and connectivity to the target server.

## Documentation and installer disagree

Run the documentation-sync workflow in a clean VM or container and update both the implementation and the wiki in the same pull request.
