/*
 * direct_surface_path_tracker.h
 *
 * Generation-bound, dependency-free bookkeeping for the Surface/RenderService
 * direct path.  The tracker deliberately distinguishes queue acceptance from
 * compositor presentation: recordQueue() never manufactures a present receipt.
 *
 * The same RouteSample schema is reserved for a future broker experiment.  It
 * is a measurement seam only; selecting Route::BROKER does not create a broker
 * process or change product topology.
 */
#ifndef DIRECT_SURFACE_PATH_TRACKER_H
#define DIRECT_SURFACE_PATH_TRACKER_H

#include <cstdint>

namespace oh_adapter {

class DirectSurfacePathTracker {
public:
    enum class Route : uint8_t {
        DIRECT = 0,
        BROKER = 1,
    };

    enum class State : uint8_t {
        UNBOUND = 0,
        LIVE,
        LOST,
        RETIRED,
    };

    enum class Result : int32_t {
        OK = 0,
        INVALID_ARGUMENT = -1,
        STALE_GENERATION = -2,
        SURFACE_LOST = -3,
        OUT_OF_ORDER = -4,
    };

    struct Snapshot {
        Route route = Route::DIRECT;
        State state = State::UNBOUND;
        int32_t sessionId = -1;
        uint64_t generation = 0;
        uint64_t surfaceId = 0;
        int32_t width = 0;
        int32_t height = 0;
        uint64_t queuedFrames = 0;
        uint64_t presentedFrames = 0;
        uint64_t resizeCount = 0;
        uint64_t lossCount = 0;
        uint64_t staleRejectCount = 0;
        uint64_t firstQueueNs = 0;
        uint64_t lastQueueNs = 0;
        uint64_t lastPresentNs = 0;
        uint64_t lastFrameId = 0;
    };

    Result bind(Route route, int32_t sessionId, uint64_t generation,
                uint64_t surfaceId, int32_t width, int32_t height)
    {
        if (sessionId < 0 || generation == 0 || surfaceId == 0 ||
            width <= 0 || height <= 0) {
            return Result::INVALID_ARGUMENT;
        }
        if (snapshot_.state == State::LIVE) {
            if (generation != snapshot_.generation) return rejectStale();
            return route == snapshot_.route &&
                    sessionId == snapshot_.sessionId &&
                    surfaceId == snapshot_.surfaceId &&
                    width == snapshot_.width &&
                    height == snapshot_.height
                ? Result::OK : Result::INVALID_ARGUMENT;
        }
        if (snapshot_.generation != 0 && generation <= snapshot_.generation) {
            return rejectStale();
        }

        const uint64_t priorLosses = snapshot_.lossCount;
        const uint64_t priorStaleRejects = snapshot_.staleRejectCount;
        snapshot_ = {};
        snapshot_.route = route;
        snapshot_.state = State::LIVE;
        snapshot_.sessionId = sessionId;
        snapshot_.generation = generation;
        snapshot_.surfaceId = surfaceId;
        snapshot_.width = width;
        snapshot_.height = height;
        snapshot_.lossCount = priorLosses;
        snapshot_.staleRejectCount = priorStaleRejects;
        return Result::OK;
    }

    Result resize(uint64_t generation, int32_t width, int32_t height)
    {
        Result gate = checkLive(generation);
        if (gate != Result::OK) return gate;
        if (width <= 0 || height <= 0) return Result::INVALID_ARGUMENT;
        if (width != snapshot_.width || height != snapshot_.height) {
            snapshot_.width = width;
            snapshot_.height = height;
            ++snapshot_.resizeCount;
        }
        return Result::OK;
    }

    Result recordQueue(uint64_t generation, uint64_t frameId, uint64_t nowNs)
    {
        Result gate = checkLive(generation);
        if (gate != Result::OK) return gate;
        if (frameId == 0 || nowNs == 0 || frameId <= snapshot_.lastFrameId) {
            return Result::OUT_OF_ORDER;
        }
        if (snapshot_.queuedFrames == 0) snapshot_.firstQueueNs = nowNs;
        snapshot_.lastQueueNs = nowNs;
        snapshot_.lastFrameId = frameId;
        ++snapshot_.queuedFrames;
        return Result::OK;
    }

    Result recordPresent(uint64_t generation, uint64_t frameId, uint64_t nowNs)
    {
        Result gate = checkLive(generation);
        if (gate != Result::OK) return gate;
        if (frameId == 0 || nowNs == 0 || frameId != snapshot_.lastFrameId ||
            snapshot_.presentedFrames >= snapshot_.queuedFrames) {
            return Result::OUT_OF_ORDER;
        }
        snapshot_.lastPresentNs = nowNs;
        ++snapshot_.presentedFrames;
        return Result::OK;
    }

    Result markLost(uint64_t generation)
    {
        if (generation != snapshot_.generation) return rejectStale();
        if (snapshot_.state == State::LOST) return Result::OK;
        if (snapshot_.state != State::LIVE) return Result::SURFACE_LOST;
        snapshot_.state = State::LOST;
        ++snapshot_.lossCount;
        return Result::OK;
    }

    Result retire(uint64_t generation)
    {
        if (generation != snapshot_.generation) return rejectStale();
        if (snapshot_.state == State::RETIRED) return Result::OK;
        if (snapshot_.state == State::UNBOUND) return Result::SURFACE_LOST;
        snapshot_.state = State::RETIRED;
        return Result::OK;
    }

    const Snapshot& snapshot() const { return snapshot_; }

    static const char* routeName(Route route)
    {
        return route == Route::DIRECT ? "direct" : "broker";
    }

private:
    Result rejectStale()
    {
        ++snapshot_.staleRejectCount;
        return Result::STALE_GENERATION;
    }

    Result checkLive(uint64_t generation)
    {
        if (generation != snapshot_.generation) return rejectStale();
        return snapshot_.state == State::LIVE
            ? Result::OK : Result::SURFACE_LOST;
    }

    Snapshot snapshot_{};
};

}  // namespace oh_adapter

#endif  // DIRECT_SURFACE_PATH_TRACKER_H
