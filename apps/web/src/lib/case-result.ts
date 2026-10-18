export async function guardCaseResult<T>(task: Promise<T> | T, isCurrent: () => boolean): Promise<T> {
  const result = await task;
  if (!isCurrent()) throw new Error("Resultado descartado por cambio de expediente o sesión.");
  return result;
}
