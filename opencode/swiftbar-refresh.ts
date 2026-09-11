export const SwiftbarRefresh = async ({ $ }) => {
  const MIN_MS = 60_000
  let last = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  const fire = async () => {
    last = Date.now()
    try {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      await $`open -g "swiftbar://refreshallplugins"`
    } catch {}
  }

  return {
    event: async ({ event }) => {
      if (event.type !== "session.idle") return
      const since = Date.now() - last
      if (since >= MIN_MS) {
        void fire()
      } else if (!timer) {
        timer = setTimeout(() => {
          timer = undefined
          void fire()
        }, MIN_MS - since)
      }
    },
  }
}
