# Infrastructure provider guides

Devsembly's core platform is designed to run on a **Development Host** rather than depend on a particular cloud vendor.

Ubuntu LTS is currently required as the Development Host operating system. Each provider guide should cover only the steps that differ by provider, such as:

- instance or VM creation;
- image selection;
- CPU, memory, and storage recommendations;
- public and private networking;
- firewall or security-group configuration;
- DNS and reverse DNS;
- SSH key placement;
- startup scripts or cloud-init;
- snapshots, backups, and recovery considerations.

After the Development Host is provisioned, users should return to the shared Devsembly installation instructions.

## Provider status

| Provider | Status | Guide |
|---|---|---|
| Vultr | Initial tested provider | [`vultr.md`](vultr.md) |
| Other providers | Planned | Add only after validation |

## Documentation maintenance requirement

When support for a provider is added or changed, update:

1. this provider index;
2. the provider guide;
3. [`../platform-support.md`](../platform-support.md);
4. the version-controlled wiki and applicable how-to guides;
5. automated provisioning and installation tests.
