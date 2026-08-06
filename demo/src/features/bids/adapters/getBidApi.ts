import type { BidApiPort } from './bidApiPort'
import { shouldUseBidMocks } from './bidEnv'
import { createMockBidApi } from './mockBidApi'

/**
 * M1 Bid API 入口。
 * - 默认关闭 Mock（与仓库 VITE_USE_MOCKS=false 一致）
 * - 仅当 VITE_USE_MOCKS=true 时自动挂载 Mock
 * - 真实后端：由调用方 setBidApi(M3 HTTP Client / 生成 SDK 封装)，本文件不手写 fetch
 */
let bidApi: BidApiPort | null = shouldUseBidMocks() ? createMockBidApi() : null

export function getBidApi(): BidApiPort {
  if (!bidApi) {
    throw new Error(
      '[M1] Bid Mock 已关闭（VITE_USE_MOCKS=false）。请先 setBidApi(...) 注入真实 API Client 后再调用。',
    )
  }
  return bidApi
}

export function setBidApi(next: BidApiPort) {
  bidApi = next
}

/** 测试或本地显式打开 Mock 时使用 */
export function resetBidApiToMock() {
  bidApi = createMockBidApi()
}

export function clearBidApi() {
  bidApi = null
}
