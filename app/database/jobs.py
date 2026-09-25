from datetime import datetime, timezone

from app.services.jobs import (
    JobCooldownError,
    JobError,
    MINIMUM_HIRE_TIME,
    WORK_COOLDOWN,
    apply_job_xp,
    apply_profile_xp,
    calculate_profile_xp,
    calculate_professional_xp,
    calculate_work_cp,
)


class JobRepository:
    """Acesso ao banco de dados do sistema de empregos."""

    def __init__(self, pool):
        self.pool = pool

    async def list_jobs(self):
        async with self.pool.acquire() as connection:
            return await connection.fetch(
                """
                SELECT
                    id,
                    name,
                    coefficient
                FROM jobs
                WHERE active = TRUE
                ORDER BY id
                """
            )

    async def get_current_job(self, user_id: int):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(
                """
                SELECT
                    j.id,
                    j.name,
                    j.coefficient,
                    jp.level,
                    jp.xp,
                    jp.last_work_at,
                    p.job_hired_at
                FROM profiles p
                JOIN jobs j
                    ON j.id = p.current_job_id
                JOIN job_progress jp
                    ON jp.user_id = p.user_id
                   AND jp.job_id = j.id
                WHERE p.user_id = $1
                """,
                user_id,
            )

    async def apply_job(self, user_id: int, job_number: int):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                profile = await connection.fetchrow(
                    """
                    SELECT
                        current_job_id
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE
                    """,
                    user_id,
                )

                if profile is None:
                    raise JobError("Seu perfil ainda não foi criado.")

                if profile["current_job_id"] is not None:
                    raise JobError(
                        "Você já possui um emprego. "
                        "Abandone o emprego atual antes de contratar outro."
                    )

                jobs = await connection.fetch(
                    """
                    SELECT
                        id,
                        name,
                        coefficient
                    FROM jobs
                    WHERE active = TRUE
                    ORDER BY id
                    """
                )

                if job_number < 1 or job_number > len(jobs):
                    raise JobError("Número de emprego inválido.")

                job = jobs[job_number - 1]

                progress = await connection.fetchrow(
                    """
                    INSERT INTO job_progress (
                        user_id,
                        job_id
                    )
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, job_id)
                    DO UPDATE SET user_id = EXCLUDED.user_id
                    RETURNING
                        level,
                        xp
                    """,
                    user_id,
                    job["id"],
                )

                hired_at = datetime.now(timezone.utc)

                await connection.execute(
                    """
                    INSERT INTO job_history (
                        user_id,
                        job_id,
                        hired_at
                    )
                    VALUES ($1, $2, $3)
                    """,
                    user_id,
                    job["id"],
                    hired_at,
                )

                await connection.execute(
                    """
                    UPDATE profiles
                    SET
                        current_job_id = $1,
                        job_hired_at = $2,
                        profession = $3,
                        profession_level = $4,
                        updated_at = NOW()
                    WHERE user_id = $5
                    """,
                    job["id"],
                    hired_at,
                    job["name"],
                    progress["level"],
                    user_id,
                )

                return {
                    "job_id": job["id"],
                    "name": job["name"],
                    "level": progress["level"],
                    "xp": progress["xp"],
                    "hired_at": hired_at,
                }

    async def abandon_job(self, user_id: int):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                profile = await connection.fetchrow(
                    """
                    SELECT
                        current_job_id,
                        job_hired_at
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE
                    """,
                    user_id,
                )

                if profile is None:
                    raise JobError("Seu perfil ainda não foi criado.")

                if profile["current_job_id"] is None:
                    raise JobError("Você não possui um emprego atualmente.")

                now = datetime.now(timezone.utc)
                hired_at = profile["job_hired_at"]

                minimum_abandon_at = hired_at + MINIMUM_HIRE_TIME

                if now < minimum_abandon_at:
                    remaining = minimum_abandon_at - now

                    hours = remaining.days * 24 + remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60

                    raise JobError(
                        "Você só pode abandonar o emprego após 24 horas "
                        f"da contratação. Faltam aproximadamente "
                        f"{hours}h {minutes}min."
                    )

                job = await connection.fetchrow(
                    """
                    SELECT
                        id,
                        name
                    FROM jobs
                    WHERE id = $1
                    """,
                    profile["current_job_id"],
                )

                await connection.execute(
                    """
                    UPDATE job_history
                    SET abandoned_at = $1
                    WHERE user_id = $2
                      AND job_id = $3
                      AND abandoned_at IS NULL
                    """,
                    now,
                    user_id,
                    profile["current_job_id"],
                )

                await connection.execute(
                    """
                    UPDATE profiles
                    SET
                        current_job_id = NULL,
                        job_hired_at = NULL,
                        profession = NULL,
                        profession_level = 0,
                        updated_at = NOW()
                    WHERE user_id = $1
                    """,
                    user_id,
                )

                return {
                    "name": job["name"],
                    "abandoned_at": now,
                }

    async def work(self, user_id: int):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                profile = await connection.fetchrow(
                    """
                    SELECT
                        current_job_id,
                        level AS profile_level,
                        xp AS profile_xp
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE
                    """,
                    user_id,
                )

                if profile is None:
                    raise JobError("Seu perfil ainda não foi criado.")

                if profile["current_job_id"] is None:
                    raise JobError(
                        "Você está desempregado. Escolha um emprego antes de trabalhar."
                    )

                job = await connection.fetchrow(
                    """
                    SELECT
                        id,
                        name,
                        coefficient
                    FROM jobs
                    WHERE id = $1
                      AND active = TRUE
                    """,
                    profile["current_job_id"],
                )

                if job is None:
                    raise JobError("Seu emprego atual não está mais disponível.")

                progress = await connection.fetchrow(
                    """
                    SELECT
                        level,
                        xp,
                        last_work_at
                    FROM job_progress
                    WHERE user_id = $1
                      AND job_id = $2
                    FOR UPDATE
                    """,
                    user_id,
                    job["id"],
                )

                if progress is None:
                    raise JobError("O progresso deste emprego não foi encontrado.")

                last_work_at = progress["last_work_at"]

                if last_work_at is not None:
                    retry_at = last_work_at + WORK_COOLDOWN

                    now = datetime.now(timezone.utc)

                    if now < retry_at:
                        raise JobCooldownError(retry_at)

                cp = calculate_work_cp(
                    job["coefficient"],
                    progress["level"],
                )

                professional_xp = calculate_professional_xp(cp)
                profile_xp = calculate_profile_xp(cp)

                new_job_progress = apply_job_xp(
                    progress["level"],
                    progress["xp"],
                    professional_xp,
                )

                new_profile_progress = apply_profile_xp(
                    profile["profile_level"],
                    profile["profile_xp"],
                    profile_xp,
                )

                now = datetime.now(timezone.utc)
                next_work_at = now + WORK_COOLDOWN

                await connection.execute(
                    """
                    UPDATE job_progress
                    SET
                        level = $1,
                        xp = $2,
                        last_work_at = $3
                    WHERE user_id = $4
                      AND job_id = $5
                    """,
                    new_job_progress["level"],
                    new_job_progress["xp"],
                    now,
                    user_id,
                    job["id"],
                )

                await connection.execute(
                    """
                    UPDATE profiles
                    SET
                        level = $1,
                        xp = $2,
                        wallet = wallet + $3,
                        profession_level = $4,
                        updated_at = NOW()
                    WHERE user_id = $5
                    """,
                    new_profile_progress["level"],
                    new_profile_progress["xp"],
                    cp,
                    new_job_progress["level"],
                    user_id,
                )

                return {
                    "job_name": job["name"],
                    "cp": cp,
                    "professional_xp": professional_xp,
                    "profile_xp": profile_xp,
                    "job_level": new_job_progress["level"],
                    "job_xp": new_job_progress["xp"],
                    "job_levels_gained": new_job_progress["levels_gained"],
                    "profile_level": new_profile_progress["level"],
                    "profile_xp_total": new_profile_progress["xp"],
                    "profile_levels_gained": (new_profile_progress["levels_gained"]),
                    "worked_at": now,
                    "next_work_at": next_work_at,
                }
