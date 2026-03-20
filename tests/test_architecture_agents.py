import asyncio
import unittest

from github_repohunter.architecture_agents import run_parallel_agents, render_architecture_markdown


class TestArchitectureAgents(unittest.TestCase):
    def test_parallel_agents_and_render(self):
        repos = [
            {
                "name": "org/repo",
                "language": "Python",
                "stars": 100,
                "url": "https://github.com/org/repo",
                "description": "reference repo",
            }
        ]
        mesh = asyncio.run(
            run_parallel_agents(
                requirement="build robust architecture generation",
                repos=repos,
                stack_preferences=["FastAPI", "PostgreSQL"],
            )
        )
        self.assertIn("planning-scope-agent", mesh)
        self.assertIn("planning-structure-agent", mesh)
        self.assertIn("quality-code-agent", mesh)
        self.assertIn("security-agent", mesh)
        self.assertIn("implementation-writer-agent", mesh)
        self.assertIn("implementation-refactor-agent", mesh)
        self.assertIn("domain_reports", mesh)
        self.assertIn("progress_updates", mesh)

        md = render_architecture_markdown(
            product_name="TestProduct",
            requirement="build robust architecture generation",
            mesh_output=mesh,
            repos=repos,
        )
        self.assertIn("Six-Agent Collaboration Model", md)
        self.assertIn("Planning Domain Report", md)
        self.assertIn("Quality and Security Domain Report", md)
        self.assertIn("Implementation Domain Report", md)
        self.assertIn("Copy-Paste Prompt For Vibe Coding Platforms", md)
        self.assertIn("TestProduct", md)


if __name__ == "__main__":
    unittest.main()
