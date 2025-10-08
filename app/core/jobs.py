import asyncio

from app.core.runner import PROCESS_JOB_TYPE, RUNNER


class JobManager:
    def __init__(self):
        self.runner = RUNNER

    def get(self, agent_key: str) -> PROCESS_JOB_TYPE:
        return self.runner.get(agent_key)

    async def start(self, agent_key: str) -> PROCESS_JOB_TYPE:
        job = self.get(agent_key)
        asyncio.create_task(job.start())
        return job

    def pause(self, agent_key: str):
        self.get(agent_key).pause()

    def resume(self, agent_key: str):
        self.get(agent_key).resume()

    def stop(self, agent_key: str):
        self.get(agent_key).stop()

    def reset(self, agent_key: str):
        self.get(agent_key).reset()


JOB_MANAGER = JobManager()
